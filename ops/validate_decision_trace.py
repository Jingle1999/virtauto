#!/usr/bin/env python3
"""
Minimal Decision Trace Validator (Record-Format only)

Requires at least 1 JSONL line with:
ts, trace_version, decision_id, actor, phase, result
Exit: 0 OK, 1 FAIL
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict

PATH = Path("ops/reports/decision_trace.jsonl")
REQUIRED = ("ts", "trace_version", "decision_id", "actor", "phase", "result")


def fail(msg: str) -> None:
    print(f"VALIDATION FAILED: {msg}")
    sys.exit(1)


def main() -> None:
    if not PATH.exists():
        fail(f"Missing {PATH}")

    lines = [ln.strip() for ln in PATH.read_text(encoding="utf-8").splitlines() if ln.strip()]
    if not lines:
        fail(f"{PATH} is empty")

    # Validate only the last line (fast) – raise N if you want.
    ln = lines[-1]
    try:
        obj: Dict[str, Any] = json.loads(ln)
    except Exception as e:
        fail(f"{PATH}: invalid JSON on last line: {e}")

    if not isinstance(obj, dict):
        fail(f"{PATH}: last line must be a JSON object")

    missing = [k for k in REQUIRED if k not in obj or obj[k] in (None, "", [])]
    if missing:
        fail(f"{PATH}: missing required keys {missing}")

    if not isinstance(obj["ts"], str):
        fail(f"{PATH}: ts must be string")
    if not isinstance(obj["trace_version"], str):
        fail(f"{PATH}: trace_version must be string")
    if not isinstance(obj["decision_id"], str):
        fail(f"{PATH}: decision_id must be string")
    if not isinstance(obj["actor"], str):
        fail(f"{PATH}: actor must be string")
    if not isinstance(obj["phase"], str):
        fail(f"{PATH}: phase must be string")

    print(f"VALIDATION OK: {PATH} (checked last record).")
    sys.exit(0)


if __name__ == "__main__":
    main()
