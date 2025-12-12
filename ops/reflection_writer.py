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
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


OPS_DIR = Path(__file__).resolve().parent
DECISIONS_DIR = OPS_DIR / "decisions"

LATEST_DECISION = DECISIONS_DIR / "latest.json"
GUARDIAN_ADVICE = DECISIONS_DIR / "guardian_advice.json"  # optional

DECISION_FILE = "ops/decisions/latest.json"
GUARDIAN_FILE = "ops/decisions/guardian_advice.json"
REFLECTION_DIR = "ops/decisions/reflections"

os.makedirs(REFLECTION_DIR, exist_ok=True)

with open(DECISION_FILE) as f:
    decision = json.load(f)

guardian_present = os.path.exists(GUARDIAN_FILE)
guardian_alignment = 0.8 if guardian_present else 0.5

timestamp = datetime.utcnow().isoformat() + "Z"

reflection = {
    "schema_version": "1.1",
    "timestamp": timestamp,
    "decision_id": decision.get("id", "unknown"),
    "orchestrator": "GEORGE",
    "inputs": {
        "decision": DECISION_FILE,
        "guardian_advice_present": guardian_present
    },
    "assessment": {
        "risk_level": decision.get("risk", "unknown"),
        "confidence": decision.get("confidence", 0.6),
        "guardian_alignment": guardian_alignment
    },
    "behavior": {
        "mode": "advisory",
        "blocking": False,
        "human_override_required": False
    },
    "learning": {
        "what_worked": [],
        "what_failed": [],
        "next_adjustments": []
    },
    "autonomy_contribution": {
        "delta": 1.5 if guardian_present else 0.5,
        "reason": "Guardian aligned advisory decision"
    }
}

out_file = f"{REFLECTION_DIR}/{timestamp}.json"
with open(out_file, "w") as f:
    json.dump(reflection, f, indent=2)

print(f"Reflection written: {out_file}")

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

    # --- Autonomy delta from reflection (v1.1) ---
    autonomy_delta = 0.0
    autonomy_reason = "neutral"

    if len(errors) > 0 or normalized in ("failure", "blocked"):
        autonomy_delta = -2.0
        autonomy_reason = "error_or_blocked"
    elif normalized == "success" and agreed and guardian_flag in ("none", "", None):
        autonomy_delta = +1.0
        autonomy_reason = "success_guardian_agreed"
    elif normalized == "success":
        autonomy_delta = +0.5
        autonomy_reason = "success_partial"
    
    reflection: Dict[str, Any] = {
        "schema_version": "1.1",
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
        "autonomy": {
        # delta comes from this reflection only (score evolution happens in a separate file)
        "delta": autonomy_delta,
        "signals": {
            "guardian_present": isinstance(guardian, dict),
            "guardian_agreed": agreed,
            "guardian_flag": guardian_flag,
            "status": normalized,
            "errors": len(errors),
        },
        "explain": f"reflection:{autonomy_reason}",
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
