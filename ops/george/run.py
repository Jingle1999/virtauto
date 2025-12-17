#!/usr/bin/env python3
"""
GEORGE Orchestrator (v0.1)

- Loads:   ops/rules/george_rules.yaml
- Reads:   ops/reports/system_status.json   (optional; safe fallback)
- Input:   --event <path-to-json>
- Selects: first matching rule (YAML order) deterministically
- Applies: preconditions gates (guardian_status, system_health_min, emergency_lock, require_human_override)
- Writes:  ops/decisions/latest.json + appends ops/decisions/decisions.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import yaml  # type: ignore
except ImportError:
    print("Missing dependency: pyyaml. Add to workflow: pip install pyyaml", file=sys.stderr)
    sys.exit(2)


# ---------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[2]  # ops/george/run.py -> repo root

RULES_FILE = REPO_ROOT / "ops" / "rules" / "george_rules.yaml"
STATUS_FILE = REPO_ROOT / "ops" / "reports" / "system_status.json"

DECISIONS_DIR = REPO_ROOT / "ops" / "decisions"
LATEST_DECISION = DECISIONS_DIR / "latest.json"
DECISIONS_LOG = DECISIONS_DIR / "decisions.jsonl"


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------
def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Rules file not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data or {}


def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:
        return {}


def write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
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


# ---------------------------------------------------------------------
# Event normalization
# ---------------------------------------------------------------------
def normalize_event(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Accepts:
      - {"agent":"...", "event":"...", "payload":{...}, "timestamp":"..."}
      - {"source_agent":"...", "type":"...", "payload":{...}}
      - {"from":"...", "name":"..."} etc.
    Returns canonical:
      {"agent": str, "event": str, "payload": dict, "timestamp": str}
    """
    agent = (
        raw.get("agent")
        or raw.get("source_agent")
        or raw.get("from")
        or raw.get("actor")
        or "unknown"
    )
    event = raw.get("event") or raw.get("type") or raw.get("name") or "unknown"

    payload = raw.get("payload")
    if not isinstance(payload, dict):
        payload = {}

    ts = raw.get("timestamp") or raw.get("ts") or raw.get("time") or now_iso()

    return {
        "agent": str(agent),
        "event": str(event),
        "payload": payload,
        "timestamp": str(ts),
    }


# ---------------------------------------------------------------------
# Status snapshot (for preconditions)
# ---------------------------------------------------------------------
def _norm_health(v: Any) -> Optional[float]:
    if v is None:
        return None
    try:
        x = float(v)
    except Exception:
        return None
    # allow 0..100 or 0..1
    if x > 1.0:
        return x / 100.0
    return x


def status_snapshot() -> Dict[str, Any]:
    """
    Minimal snapshot for gating.
    - Tries to read ops/reports/system_status.json (if present)
    - Supports multiple shapes:
        { "health": { "overall_health": 0.8, "metrics": {...} }, "guardian": {"status":"green"}, "autonomy": {...} }
        { "system_health": 0.8, "guardian_status": "green" }
    """
    raw = load_json(STATUS_FILE)

    # metrics / autonomy sections
    metrics: Dict[str, Any] = {}
    if isinstance(raw.get("health"), dict):
        metrics = raw.get("health", {}).get("metrics", {}) if isinstance(raw.get("health", {}).get("metrics"), dict) else {}
    elif isinstance(raw.get("metrics"), dict):
        metrics = raw.get("metrics", {})

    autonomy: Dict[str, Any] = raw.get("autonomy", {}) if isinstance(raw.get("autonomy"), dict) else {}

    # guardian status
    guardian_status = None
    if isinstance(raw.get("guardian"), dict):
        guardian_status = raw.get("guardian", {}).get("status")
    if guardian_status is None:
        guardian_status = raw.get("guardian_status")

    # system health
    system_health = None
    if isinstance(raw.get("health"), dict):
        system_health = raw.get("health", {}).get("overall_health")
    if system_health is None:
        system_health = raw.get("system_health")

    return {
        "guardian_status": (str(guardian_status) if guardian_status is not None else "unknown"),
        "system_health": _norm_health(system_health),
        "autonomy_level": autonomy.get("current_level") if isinstance(autonomy, dict) else None,
        "raw": raw,
        "metrics": metrics or {},
    }


# ---------------------------------------------------------------------
# Matching & gating
# ---------------------------------------------------------------------
def preconditions_ok(rule: Dict[str, Any], snap: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Supported preconditions (all optional):
      preconditions:
        guardian_status: ["green","yellow"]
        system_health_min: 0.6
        emergency_lock: false
        require_human_override: true   (if true, requires payload.human_override == true)
    """
    reasons: List[str] = []
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
            min_h_f = float(min_h)
        except Exception:
            min_h_f = None
        current_h = snap.get("system_health")
        if min_h_f is not None:
            if current_h is None:
                reasons.append("system_health is missing (cannot evaluate system_health_min)")
            elif float(current_h) < min_h_f:
                reasons.append(f"system_health {float(current_h):.3f} < min {min_h_f:.3f}")

    # emergency_lock (if true -> block)
    if bool(pre.get("emergency_lock", False)) is True:
        reasons.append("emergency_lock is enabled")

    # require_human_override (handled later in build_decision using event payload)
    # We keep it as a precondition marker; evaluation in build_decision for better messaging.

    return (len(reasons) == 0), reasons


def matches(rule: Dict[str, Any], ev: Dict[str, Any]) -> bool:
    m = rule.get("match") or {}
    if not isinstance(m, dict):
        return False

    # Catch-all: match: {}
    if not m:
        return True

    # agent match (optional)
    rule_agents = m.get("agent")
    if rule_agents is not None:
        allowed_agents = [str(x) for x in coerce_list(rule_agents)]
        if ev.get("agent") not in allowed_agents:
            return False

    # event match (optional)
    rule_events = m.get("event")
    if rule_events is not None:
        allowed_events = [str(x) for x in coerce_list(rule_events)]
        if ev.get("event") not in allowed_events:
            return False

    return True


def select_rule(rules: List[Dict[str, Any]], ev: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    # Deterministic: first match wins (YAML order)
    for r in rules:
        if matches(r, ev):
            return r
    return None


# ---------------------------------------------------------------------
# Decision building
# ---------------------------------------------------------------------
def build_decision(ev: Dict[str, Any], rule: Optional[Dict[str, Any]], snap: Dict[str, Any]) -> Dict[str, Any]:
    decision: Dict[str, Any] = {
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
    action = rule.get("action") or {}
    decision["action"] = action if isinstance(action, dict) else {}

    ok, reasons = preconditions_ok(rule, snap)

    # require_human_override: if true, require ev.payload.human_override == true
    pre = rule.get("preconditions") or {}
    if isinstance(pre, dict) and pre.get("require_human_override") is True:
        human_override = bool(ev.get("payload", {}).get("human_override", False))
        if not human_override:
            ok = False
            reasons.append("require_human_override is true but event.payload.human_override is not true")

    decision["allowed"] = ok
    decision["blocked_reasons"] = reasons

    # If blocked: convert to safe HOLD routed to self_guardian, preserving original action
    if not ok:
        decision["action"] = {
            "type": "hold",
            "target_agent": "self_guardian",
            "intent": "review_blocked_action",
            "message": "Action blocked by GEORGE preconditions; routed to Self-Guardian for review.",
            "original_action": action if isinstance(action, dict) else {},
        }

    return decision


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--event", required=True, help="Path to event JSON file")
    ap.add_argument("--print", action="store_true", help="Print decision JSON to stdout")
    args = ap.parse_args()

    event_path = Path(args.event)
    if not event_path.exists():
        print(f"Event file not found: {event_path}", file=sys.stderr)
        return 2

    try:
        raw_event = json.loads(event_path.read_text(encoding="utf-8"))
        if not isinstance(raw_event, dict):
            raise ValueError("event JSON must be an object/dict")
    except Exception as e:
        print(f"Failed to read/parse event JSON: {e}", file=sys.stderr)
        return 2

    ev = normalize_event(raw_event)

    # load rules
    try:
        rules_doc = load_yaml(RULES_FILE)
    except Exception as e:
        print(f"Failed to load rules YAML: {e}", file=sys.stderr)
        return 1

    rules = rules_doc.get("rules") or []
    if not isinstance(rules, list):
        print("Invalid george_rules.yaml: 'rules' must be a list", file=sys.stderr)
        return 2

    # snapshot + decision
    snap = status_snapshot()
    rule = select_rule(rules, ev)
    decision = build_decision(ev, rule, snap)

    # persist
    try:
        DECISIONS_DIR.mkdir(parents=True, exist_ok=True)
        write_json(LATEST_DECISION, decision)
        append_jsonl(DECISIONS_LOG, decision)
    except Exception as e:
        print(f"Failed to persist decisions: {e}", file=sys.stderr)
        return 1

    if args.print:
        print(json.dumps(decision, ensure_ascii=False, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
