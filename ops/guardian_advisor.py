#!/usr/bin/env python3
"""
Guardian Advisor (non-blocking)

Reads latest decision from ops/decisions/latest.json
Writes advisory output to ops/decisions/guardian_advice.json

Design goals:
- No external deps
- Tolerant to schema differences:
  - latest.json may be a list (legacy) or a dict (v2)
- Never "blocks" -> only recommends
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

LATEST_PATH = os.environ.get("GEORGE_LATEST_PATH", "ops/decisions/latest.json")
ADVICE_PATH = os.environ.get("GUARDIAN_ADVICE_PATH", "ops/decisions/guardian_advice.json")


# --- helpers ---------------------------------------------------------------

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: str, data: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def normalize_latest(latest: Any) -> Dict[str, Any]:
    """
    Accepts:
      - dict (new schema)
      - list (legacy), takes last element if list is non-empty
    Returns a dict decision object.
    """
    if isinstance(latest, dict):
        return latest
    if isinstance(latest, list):
        return latest[-1] if latest else {}
    return {}


def safe_get(d: Dict[str, Any], *keys: str, default=None):
    cur: Any = d
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


# --- policy rules ----------------------------------------------------------

SUSPICIOUS_PATTERNS = [
    r"\brm\s+-rf\b",
    r"\bsudo\b",
    r"\bcurl\b.*\|\s*(bash|sh)\b",
    r"\bwget\b.*\|\s*(bash|sh)\b",
    r"\bchmod\s+\+x\b",
    r"\bsecrets?\b",
    r"\btoken\b",
]

HIGH_RISK_ACTIONS = {
    "deploy",
    "site-deploy",
    "rollback",
    "delete",
    "write_policies",
    "change_workflows",
}


def assess(decision: Dict[str, Any]) -> Tuple[str, float, str, list]:
    """
    Returns: (recommendation, confidence, flag, notes[])
    recommendation: proceed | proceed_with_caution | halt_for_review
    flag: None | "security_risk" | "policy_violation" | "insufficient_context"
    """
    notes = []

    action = safe_get(decision, "action") or safe_get(decision, "trigger") or safe_get(decision, "decision")
    reason = safe_get(decision, "reason") or ""
    intent = safe_get(decision, "intent") or ""
    summary = safe_get(decision, "result_summary") or ""

    text = " ".join(str(x) for x in [action, reason, intent, summary] if x is not None).strip().lower()

    if not text:
        return "proceed_with_caution", 0.55, "insufficient_context", ["No meaningful fields found in latest.json"]

    # pattern-based security heuristics
    hits = []
    for pat in SUSPICIOUS_PATTERNS:
        if re.search(pat, text, flags=re.IGNORECASE):
            hits.append(pat)

    # action-based risk
    action_norm = str(action).strip().lower() if action is not None else ""
    high_risk_action = action_norm in HIGH_RISK_ACTIONS

    # scoring
    risk = 0
    if hits:
        risk += 2
        notes.append(f"Suspicious pattern(s) detected: {len(hits)}")
    if high_risk_action:
        risk += 1
        notes.append(f"High-risk action detected: {action_norm}")

    # decide recommendation
    if risk >= 2:
        return "halt_for_review", 0.90, "security_risk", notes
    if risk == 1:
        return "proceed_with_caution", 0.75, None, notes
    return "proceed", 0.85, None, ["No policy risks detected"]


def main() -> int:
    try:
        latest_raw = load_json(LATEST_PATH)
    except FileNotFoundError:
        advice = {
            "schema_version": "1.0",
            "timestamp": utc_now_iso(),
            "mode": "advisor",
            "recommendation": "proceed_with_caution",
            "confidence": 0.55,
            "flag": "insufficient_context",
            "notes": [f"latest.json not found at {LATEST_PATH}"],
        }
        save_json(ADVICE_PATH, advice)
        print(f"[guardian_advisor] latest.json missing -> wrote advisory to {ADVICE_PATH}")
        return 0
    except Exception as e:
        advice = {
            "schema_version": "1.0",
            "timestamp": utc_now_iso(),
            "mode": "advisor",
            "recommendation": "halt_for_review",
            "confidence": 0.90,
            "flag": "policy_violation",
            "notes": [f"Failed to read/parse latest.json: {e}"],
        }
        save_json(ADVICE_PATH, advice)
        print(f"[guardian_advisor] error reading latest.json -> wrote advisory to {ADVICE_PATH}")
        return 0

    latest = normalize_latest(latest_raw)
    recommendation, confidence, flag, notes = assess(latest)

    advice = {
        "schema_version": "1.0",
        "timestamp": utc_now_iso(),
        "mode": "advisor",
        "recommendation": recommendation,
        "confidence": float(round(confidence, 2)),
        "flag": flag,
        "notes": notes,
        "inputs": {
            "latest_path": LATEST_PATH,
            "action": safe_get(latest, "action") or safe_get(latest, "trigger") or safe_get(latest, "decision"),
            "agent": safe_get(latest, "agent"),
            "source_event_id": safe_get(latest, "source_event_id"),
            "decision_id": safe_get(latest, "decision_id") or safe_get(latest, "id"),
        },
    }

    save_json(ADVICE_PATH, advice)
    print(f"[guardian_advisor] wrote advisory: {recommendation} (conf={advice['confidence']}) -> {ADVICE_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
