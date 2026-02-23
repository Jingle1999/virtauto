#!/usr/bin/env python3
"""
Decision Trace Validator (Contract-aligned, strict)

Validates ops/reports/decision_trace.jsonl as a JSONL stream where EACH line is a
trace record.

Requirements per record (minimum):
  ts, trace_version, decision_id, actor, phase, result

Contract alignment:
  - trace_version must be "v1"
  - phase must be one of:
      route
      guardian_precheck
      authority_enforcement
      execute_or_blocked
      guardian_postcheck
      finalize

Exit: 0 OK, 1 FAIL
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

PATH = Path("ops/reports/decision_trace.jsonl")

REQUIRED = ("ts", "trace_version", "decision_id", "actor", "phase", "result")

ALLOWED_TRACE_VERSION = "v1"

ALLOWED_PHASES = {
    "route",
    "guardian_precheck",
    "authority_enforcement",
    "execute_or_blocked",
    "guardian_postcheck",
    "finalize",
}


def fail(msg: str) -> None:
    print(f"VALIDATION FAILED: {msg}")
    sys.exit(1)


def _parse_iso(ts: str) -> bool:
    """
    Minimal ISO 8601 validation.
    Accepts:
      - 'Z' suffix (UTC)
      - '+00:00' offset
      - naive ISO (still parseable) — but recommended to be UTC/Z.
    """
    if not isinstance(ts, str) or not ts.strip():
        return False
    s = ts.strip()
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        datetime.fromisoformat(s)
        return True
    except Exception:
        return False


def main() -> None:
    if not PATH.exists():
        fail(f"Missing {PATH}")

    lines: List[str] = [
        ln.strip()
        for ln in PATH.read_text(encoding="utf-8").splitlines()
        if ln.strip()
    ]
    if not lines:
        fail(f"{PATH} is empty")

    # Validate ALL lines (strict)
    for idx, ln in enumerate(lines, start=1):
        try:
            obj: Dict[str, Any] = json.loads(ln)
        except Exception as e:
            fail(f"{PATH}: invalid JSON at line {idx}: {e}")

        if not isinstance(obj, dict):
            fail(f"{PATH}: line {idx} must be a JSON object")

        missing = [k for k in REQUIRED if k not in obj or obj[k] in (None, "", [])]
        if missing:
            fail(f"{PATH}: line {idx} missing required keys {missing}")

        # Types
        for k in REQUIRED:
            if not isinstance(obj[k], str):
                fail(f"{PATH}: line {idx} '{k}' must be string")

        # ts format (minimal)
        if not _parse_iso(obj["ts"]):
            fail(f"{PATH}: line {idx} ts not ISO-parseable: {obj['ts']}")

        # trace_version strict
        if obj["trace_version"] != ALLOWED_TRACE_VERSION:
            fail(
                f"{PATH}: line {idx} trace_version must be '{ALLOWED_TRACE_VERSION}', "
                f"got '{obj['trace_version']}'"
            )

        # phase vocabulary strict (Frozen Contract)
        if obj["phase"] not in ALLOWED_PHASES:
            fail(
                f"{PATH}: line {idx} phase '{obj['phase']}' not allowed. "
                f"Allowed: {sorted(ALLOWED_PHASES)}"
            )

    print(f"VALIDATION OK: {PATH} (checked {len(lines)} records).")
    sys.exit(0)


if __name__ == "__main__":
    main()