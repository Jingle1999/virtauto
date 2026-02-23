#!/usr/bin/env python3
"""
Decision Trace Ledger Validator (Append-only, Record-format)

This validator treats ops/reports/decision_trace.jsonl as an append-only ledger.

Hard rules:
- File must exist and contain at least 1 non-empty JSONL record.
- EVERY line must be a JSON object in record format (no meta/schema lines).
- Required keys must be present and non-empty:
  ts, trace_version, decision_id, actor, phase, result
- decision_id MUST be unique across the whole ledger (prevents overwrites).
- ts MUST be a string and MUST NOT go backwards (monotonic non-decreasing).

Exit: 0 OK, 1 FAIL
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

PATH = Path("ops/reports/decision_trace.jsonl")
REQUIRED: Tuple[str, ...] = ("ts", "trace_version", "decision_id", "actor", "phase", "result")


def fail(msg: str) -> None:
    print(f"VALIDATION FAILED: {msg}")
    sys.exit(1)


def _load_lines() -> List[str]:
    if not PATH.exists():
        fail(f"Missing {PATH}")

    lines = [ln.strip() for ln in PATH.read_text(encoding="utf-8").splitlines() if ln.strip()]
    if not lines:
        fail(f"{PATH} is empty")
    return lines


def _parse_obj(idx: int, ln: str) -> Dict[str, Any]:
    try:
        obj = json.loads(ln)
    except Exception as e:
        fail(f"{PATH}: invalid JSON at line {idx}: {e}")

    if not isinstance(obj, dict):
        fail(f"{PATH}: line {idx} must be a JSON object")
    return obj


def _validate_required(idx: int, obj: Dict[str, Any]) -> None:
    missing = [k for k in REQUIRED if k not in obj or obj[k] in (None, "", [])]
    if missing:
        fail(f"{PATH}: line {idx} missing required keys {missing}")

    # type checks
    for k in REQUIRED:
        if not isinstance(obj[k], str):
            fail(f"{PATH}: line {idx} key '{k}' must be string")

    # quick sanity (avoid accidental meta-records)
    if obj.get("schema_version") is not None and "decision_id" not in obj:
        fail(f"{PATH}: line {idx} looks like a meta/schema record; ledger must contain record-format only")

    if not obj["phase"].strip():
        fail(f"{PATH}: line {idx} phase must not be empty")


def main() -> None:
    lines = _load_lines()

    seen_ids: Set[str] = set()
    prev_ts: str | None = None

    # Validate ALL lines (ledger integrity)
    for i, ln in enumerate(lines, start=1):
        obj = _parse_obj(i, ln)
        _validate_required(i, obj)

        decision_id = obj["decision_id"]
        if decision_id in seen_ids:
            fail(f"{PATH}: duplicate decision_id '{decision_id}' found (line {i})")
        seen_ids.add(decision_id)

        ts = obj["ts"]
        # monotonic (string compare works for ISO8601 Z / +00:00 style if consistent)
        if prev_ts is not None and ts < prev_ts:
            fail(f"{PATH}: non-monotonic ts at line {i} (ts={ts} < prev_ts={prev_ts})")
        prev_ts = ts

    print(f"VALIDATION OK: {PATH} (checked {len(lines)} ledger records, unique ids, monotonic ts).")
    sys.exit(0)


if __name__ == "__main__":
    main()