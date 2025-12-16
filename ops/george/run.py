#!/usr/bin/env python3
"""
GEORGE Orchestrator (v0.1)
- Loads ops/rules/george_rules.yaml
- Takes an event JSON (agent,event,payload)
- Selects the first matching rule deterministically
- Enforces preconditions (gates)
- Writes ops/decisions/latest.json and appends ops/decisions/decisions.jsonl
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import yaml  # pyyaml
except ImportError:
    print("Missing dependency: pyyaml. Add it to your workflow (pip install pyyaml).", file=sys.stderr)
    sys.exit(2)


REPO_ROOT = Path(__file__).resolve().parents[2]  # ops/george/run.py -> repo root
RULES_FILE = REPO_ROOT / "ops" / "rules" / "george_rules.yaml"
STATUS_FILE = REPO_ROOT / "ops" / "reports" / "system_status.json"

DECISIONS_DIR = REPO_ROOT / "ops" / "decisions"
LATEST_DECISION = DECISIONS_DIR / "latest.json"
DECISIONS_LOG = DECISIONS_DIR / "decisions.jsonl"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Rules file not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # Atomic replace (same filesystem)
    tmp.replace(path)



def append_jsonl(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def coerce_list(x: Any) -> List[Any]:
    if x is None:
        return []
    if isinstance(x, list):
        return x
    return [x]


def normalize_event(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Expected:
      { "agent": "...", "event": "...", "payload": {...}, "timestamp": "..." }
    """
    agent = raw.get("agent") or raw.get("source_agent") or raw.get("from") or ""
    event = raw.get("event") or raw.get("type") or raw.get("name") or ""
    payload = raw.get("payload") if isinstance(raw.get("payload"), dict) else {}
    ts = raw.get("timestamp") or raw.get("ts") or now_iso()
    return {"agent": str(agent), "event": str(event), "payload": payload, "timestamp": ts}


def status_snapshot() -> Dict[str, Any]:
    """
    Minimal snapshot for gating.
    Tries to read ops/reports/system_status.json, but safely falls back.
    """
    raw = load_json(STATUS_FILE)

    # Supports either flat or nested format
    metrics = (raw.get("health") or {}).get("metrics") if isinstance(raw.get("health"), dict) else {}
    autonomy = raw.get("autonomy") if isinstance(raw.get("autonomy"), dict) else {}

    guardian_status = (
        (raw.get("guardian") or {}).get("status")
        if isinstance(raw.get("guardian"), dict)
        else raw.get("guardian_status")
    )

    system_health = (
        (raw.get("health") or {}).get("overall_health")
        if isinstance(raw.get("health"), dict)
        else raw.get("system_health")
    )

    # Some repos use 0..1, others 0..100
    # We normalize to 0..1 when possible.
    def norm_health(v: Any) -> Optional[float]:
        if v is None:
            return None
        try:
            x = float(v)
        except Exception:
            return None
        if x > 1.0:
            return x / 100.0
        return x

    return {
        "guardian_status": guardian_status or "unknown",
        "system_health": norm_health(system_health),
        "autonomy_level": autonomy.get("current_level") if isinstance(autonomy, dict) else None,
        "raw": raw,
        "metrics": metrics or {},
    }


def preconditions_ok(rule: Dict[str, Any], snap: Dict[str, Any]) -> (bool, List[str]):
    """
    Supported preconditions:
      preconditions:
        guardian_status: ["green","yellow"]
        system_health_min: 0.6
    """
    reasons = []
    pre = rule.get("preconditions") or {}
    if not isinstance(pre, dict):
        return True, reasons

    # guardian_status gate
    allowed = pre.get("guardian_status")
    if allowed is not None:
        allowed_list = [str(x).lower() for x in coerce_list(allowed)]
        current = str(snap.get("guardian_status") or "unknown").lower()
        if current not in allowed_list:
            reasons.append(f"guardian_status '{current}' not in allowed {allowed_list}")

    # system_health_min gate
    min_h = pre.get("system_health_min")
    if min_h is not None:
        try:
            min_h = float(min_h)
        except Exception:
            min_h = None
        current_h = snap.get("system_health")
        if min_h is not None:
            if current_h is None:
                reasons.append("system_health is missing (cannot evaluate system_health_min)")
            elif float(current_h) < min_h:
                reasons.append(f"system_health {current_h:.3f} < min {min_h:.3f}")

    return (len(reasons) == 0), reasons


def matches(rule: Dict[str, Any], ev: Dict[str, Any]) -> bool:
    m = rule.get("match") or {}
    if not isinstance(m, dict):
        return False

    # agent match
    rule_agents = m.get("agent")
    if rule_agents is not None:
        allowed_agents = [str(x) for x in coerce_list(rule_agents)]
        if ev["agent"] not in allowed_agents:
            return False

    # event match
    rule_events = m.get("event")
    if rule_events is not None:
        allowed_events = [str(x) for x in coerce_list(rule_events)]
        if ev["event"] not in allowed_events:
            return False

    return True


def select_rule(rules: List[Dict[str, Any]], ev: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Deterministic: first match wins (YAML order).
    """
    for r in rules:
        if matches(r, ev):
            return r
    return None


def build_decision(ev: Dict[str, Any], rule: Optional[Dict[str, Any]], snap: Dict[str, Any]) -> Dict[str, Any]:
    decision = {
        "timestamp": now_iso(),
        "input_event": ev,
        "rules_file": str(RULES_FILE.relative_to(REPO_ROOT)),
        "status_snapshot": {
            "guardian_status": snap.get("guardian_status"),
            "system_health": snap.get("system_health"),
        },
        "selected_rule_id": None,
        "action": None,
        "allowed": False,
        "blocked_reasons": [],
    }

    if rule is None:
        decision["selected_rule_id"] = None
        decision["action"] = {"type": "noop", "message": "No matching rule found (default noop)."}
        decision["allowed"] = True
        return decision

    decision["selected_rule_id"] = rule.get("id")
    decision["action"] = rule.get("action") or {}

    ok, reasons = preconditions_ok(rule, snap)
    decision["allowed"] = ok
    decision["blocked_reasons"] = reasons

    # If blocked → convert to safe HOLD/ESCALATE
    if not ok:
        decision["action"] = {
            "type": "hold",
            "target_agent": "self_guardian",
            "intent": "review_blocked_action",
            "message": "Action blocked by GEORGE preconditions; routed to Self-Guardian for review.",
            "original_action": rule.get("action") or {},
        }

    return decision


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--event", required=True, help="Path to event JSON file")
    ap.add_argument("--print", action="store_true", help="Print decision JSON to stdout")
    args = ap.parse_args()

    event_path = Path(args.event)
    if not event_path.exists():
        print(f"Event file not found: {event_path}", file=sys.stderr)
        return 2

    raw_event = json.loads(event_path.read_text(encoding="utf-8"))
    ev = normalize_event(raw_event)

    rules_doc = load_yaml(RULES_FILE)
    rules = rules_doc.get("rules") or []
    if not isinstance(rules, list):
        print("Invalid george_rules.yaml: 'rules' must be a list", file=sys.stderr)
        return 2

    snap = status_snapshot()
    rule = select_rule(rules, ev)
    decision = build_decision(ev, rule, snap)

    # Persist decisions
    DECISIONS_DIR.mkdir(parents=True, exist_ok=True)
    write_json(LATEST_DECISION, decision)
    append_jsonl(DECISIONS_LOG, decision)

    if args.print:
        print(json.dumps(decision, ensure_ascii=False, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
