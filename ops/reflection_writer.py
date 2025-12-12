#!/usr/bin/env python3
"""
reflection_writer.py
Creates a machine-readable Reflection from:
- ops/decisions/latest.json
- optional ops/decisions/guardian_advice.json
and persists it to:
- ops/decisions/reflections/<decision_id>.json
- ops/decisions/reflections/latest_reflection.json
- ops/decisions/reflections/history/YYYY-MM-DD.jsonl
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


OPS_DIR = Path(__file__).resolve().parent
DECISIONS_DIR = OPS_DIR / "decisions"

LATEST_DECISION = DECISIONS_DIR / "latest.json"
GUARDIAN_ADVICE = DECISIONS_DIR / "guardian_advice.json"  # optional

REFLECTIONS_DIR = DECISIONS_DIR / "reflections"
REFLECTIONS_HISTORY_DIR = REFLECTIONS_DIR / "history"
LATEST_REFLECTION = REFLECTIONS_DIR / "latest_reflection.json"

STATUS_FILE = OPS_DIR / "status.json"  # optional, for deltas


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return default


def save_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def append_jsonl(path: Path, record: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def normalize_status(raw: Optional[str]) -> str:
    """
    Map decision.status to one of: success|failure|blocked|skipped
    Your code uses: success|error|blocked|pending|...
    """
    if not raw:
        return "unknown"
    s = raw.strip().lower()
    if s in ("success", "succeeded", "ok"):
        return "success"
    if s in ("error", "failed", "failure"):
        return "failure"
    if s in ("blocked", "block"):
        return "blocked"
    if s in ("skipped", "noop", "no_action"):
        return "skipped"
    if s in ("pending",):
        return "unknown"
    return s


def derive_trigger(decision: Dict[str, Any]) -> str:
    # Simple: action or intent as trigger label
    return str(decision.get("action") or decision.get("intent") or "orchestrate")


def make_reflection(
    decision: Dict[str, Any],
    guardian: Optional[Dict[str, Any]],
    status: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    decision_id = str(decision.get("id") or "unknown")
    ts = now_iso()

    # Guardian interpretation (optional file, best-effort)
    guardian_mode = "advisor"
    guardian_flag = "none"
    policy_ids = []
    recommendation = None
    agreed = True

    if isinstance(guardian, dict) and guardian:
        guardian_mode = str(guardian.get("mode") or guardian.get("guardian_mode") or "advisor")
        guardian_flag = str(guardian.get("flag") or guardian.get("guardian_flag") or "none")
        policy_ids_raw = guardian.get("policy_ids") or guardian.get("policies") or []
        if isinstance(policy_ids_raw, list):
            policy_ids = [str(x) for x in policy_ids_raw]
        recommendation = guardian.get("recommendation") or guardian.get("advice")
        agreed_val = guardian.get("agreed_with_decision")
        if isinstance(agreed_val, bool):
            agreed = agreed_val

    # Deltas (optional, from status.json if present)
    health_delta = 0.0
    autonomy_delta = 0.0
    if isinstance(status, dict) and status:
        # If you later add previous values, you can compute real deltas.
        # For now, keep 0 unless explicit deltas exist.
        health_delta = float(status.get("health_delta", 0.0) or 0.0)
        autonomy_delta = float(status.get("autonomy_delta", 0.0) or 0.0)

    # Outcome heuristic
    normalized = normalize_status(decision.get("status"))
    observed = "unknown"
    if normalized == "success":
        observed = "positive"
    elif normalized in ("failure", "blocked"):
        observed = "negative"

    errors = []
    err_msg = decision.get("error_message")
    if err_msg:
        errors.append({"code": "decision_error", "message": str(err_msg)})

    reflection: Dict[str, Any] = {
        "schema_version": "1.0",
        "reflection_id": f"ref-{ts}",
        "decision_id": decision_id,
        "timestamp": ts,
        "context": {
            "source": "GEORGE",
            "trigger": derive_trigger(decision),
            "event_id": decision.get("source_event_id"),
            "branch": None,
            "run_url": None,
        },
        "decision_summary": {
            "selected_action": decision.get("action"),
            "selected_agent": decision.get("agent"),
            "status": normalized,
            "confidence": float(decision.get("confidence", 0.0) or 0.0),
            "reason": decision.get("result_summary") or decision.get("follow_up") or None,
        },
        "guardian_feedback": {
            "mode": guardian_mode,
            "flag": guardian_flag if guardian_flag else ("none" if normalized == "success" else "warn"),
            "policy_ids": policy_ids,
            "recommendation": recommendation,
            "agreed_with_decision": agreed,
        },
        "outcome": {
            "observed_effect": observed,
            "health_delta": health_delta,
            "autonomy_delta": autonomy_delta,
            "errors": errors,
        },
        "learning": {
            "repeated_pattern": False,
            "similar_decisions": [],
            "rule_hits": [],
            "suggested_rule_changes": [],
        },
        "notes": {
            "short": "Auto-generated reflection from latest decision."
        },
    }

    # If decision already carries guardian_flag, use it
    if decision.get("guardian_flag"):
        reflection["guardian_feedback"]["flag"] = str(decision["guardian_flag"])

    return reflection


def main() -> int:
    if not LATEST_DECISION.exists():
        print(f"[reflection_writer] Missing {LATEST_DECISION}. Nothing to do.")
        return 0

    decision = load_json(LATEST_DECISION, default={})
    if not isinstance(decision, dict) or not decision.get("id"):
        print("[reflection_writer] latest.json invalid or missing decision id.")
        return 1

    guardian = load_json(GUARDIAN_ADVICE, default=None)
    status = load_json(STATUS_FILE, default=None)

    REFLECTIONS_DIR.mkdir(parents=True, exist_ok=True)
    REFLECTIONS_HISTORY_DIR.mkdir(parents=True, exist_ok=True)

    reflection = make_reflection(decision, guardian, status)

    decision_id = reflection["decision_id"]
    per_decision_path = REFLECTIONS_DIR / f"{decision_id}.json"
    save_json(per_decision_path, reflection)
    save_json(LATEST_REFLECTION, reflection)

    day = datetime.now(timezone.utc).date().isoformat()
    history_path = REFLECTIONS_HISTORY_DIR / f"{day}.jsonl"
    append_jsonl(history_path, reflection)

    print(f"[reflection_writer] Wrote reflection: {per_decision_path}")
    print(f"[reflection_writer] Updated: {LATEST_REFLECTION}")
    print(f"[reflection_writer] Appended: {history_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
