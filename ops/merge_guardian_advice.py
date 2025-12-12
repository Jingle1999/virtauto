#!/usr/bin/env python3
"""
Merge guardian advice into ops/decisions/latest.json

- Supports latest.json as dict (new schema) OR list (legacy)
- Writes back latest.json in-place
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict


LATEST_PATH = os.environ.get("GEORGE_LATEST_PATH", "ops/decisions/latest.json")
ADVICE_PATH = os.environ.get("GUARDIAN_ADVICE_PATH", "ops/decisions/guardian_advice.json")


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


def ensure_guardian_block(target: Dict[str, Any]) -> Dict[str, Any]:
    if "guardian" not in target or not isinstance(target["guardian"], dict):
        target["guardian"] = {}
    return target["guardian"]


def main() -> int:
    if not os.path.exists(ADVICE_PATH):
        print(f"[merge_guardian_advice] No advice file at {ADVICE_PATH}. Nothing to merge.")
        return 0

    try:
        advice = load_json(ADVICE_PATH)
    except Exception as e:
        print(f"[merge_guardian_advice] Failed to read advice: {e}")
        return 0

    try:
        latest = load_json(LATEST_PATH)
    except FileNotFoundError:
        # create minimal latest.json if missing
        latest = {
            "schema_version": "2.0",
            "decision_id": "uuid",
            "timestamp": utc_now_iso(),
            "agent": "system",
            "decision": "proceed",
            "status": "success",
        }
    except Exception as e:
        print(f"[merge_guardian_advice] Failed to read latest.json: {e}")
        return 0

    # Merge
    if isinstance(latest, dict):
        guardian = ensure_guardian_block(latest)
        guardian.update(advice)
        guardian.setdefault("merged_at", utc_now_iso())
        save_json(LATEST_PATH, latest)
        print("[merge_guardian_advice] merged advice into latest.json (dict schema).")
        return 0

    if isinstance(latest, list) and latest:
        if not isinstance(latest[-1], dict):
            latest[-1] = {"timestamp": utc_now_iso(), "status": "unknown"}
        guardian = ensure_guardian_block(latest[-1])
        guardian.update(advice)
        guardian.setdefault("merged_at", utc_now_iso())
        save_json(LATEST_PATH, latest)
        print("[merge_guardian_advice] merged advice into latest.json (legacy list schema).")
        return 0

    print("[merge_guardian_advice] latest.json has unexpected structure; nothing merged.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
