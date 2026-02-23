#!/usr/bin/env python3
"""
Decision Trace Ledger Validator (Append-only, Record-format, HARD record_id)

Validates ops/reports/decision_trace.jsonl as an append-only ledger where EACH line is a trace record.

Hard rules:
- File must exist and contain at least 1 non-empty JSONL record.
- EVERY line must be a JSON object in record format (no meta/schema lines).
- Required keys must be present and non-empty:
  ts, trace_version, record_id, decision_id, actor, phase, result
- record_id MUST be unique across the whole ledger (prevents overwrites / ambiguous records).
- ts MUST be monotonic non-decreasing across the whole file (string compare works if ISO8601 is consistent).

Exit: 0 OK, 1 FAIL
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

PATH = Path("ops/reports/decision_trace.jsonl")

REQUIRED: Tuple[str, ...] = (
    "ts",
    "trace_version",
    "record_id",
    "decision_id",
    "actor",
    "phase",
    "result",
)


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

    # type checks for required keys
    for k in REQUIRED:
        if not isinstance(obj[k], str):
            fail(f"{PATH}: line {idx} key '{k}' must be string")

    # quick sanity: reject meta/schema-ish lines
    if obj.get("schema_version") is not None and "decision_id" not in obj:
        fail(
            f"{PATH}: line {idx} looks like a meta/schema record; ledger must contain record-format only"
        )

    if not obj["phase"].strip():
        fail(f"{PATH}: line {idx} phase must not be empty")


def main() -> None:
    lines = _load_lines()

    seen_record_ids: Set[str] = set()
    prev_ts: str | None = None

    for i, ln in enumerate(lines, start=1):
        obj = _parse_obj(i, ln)
        _validate_required(i, obj)

        record_id = obj["record_id"]
        if record_id in seen_record_ids:
            fail(f"{PATH}: duplicate record_id '{record_id}' found (line {i})")
        seen_record_ids.add(record_id)

        ts = obj["ts"]
        # monotonic (string compare works for ISO8601 Z / +00:00 if consistent)
        if prev_ts is not None and ts < prev_ts:
            fail(f"{PATH}: non-monotonic ts at line {i} (ts={ts} < prev_ts={prev_ts})")
        prev_ts = ts

    print(
        f"VALIDATION OK: {PATH} (checked {len(lines)} ledger records, unique record_id, monotonic ts)."
    )
    sys.exit(0)


if __name__ == "__main__":
    main()