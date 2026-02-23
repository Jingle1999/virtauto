#!/usr/bin/env python3
"""
Decision Trace Ledger Validator (Append-only, Record-format)

Validates ops/reports/decision_trace.jsonl as an append-only ledger where EACH line is a trace record.

Hard rules:
- File must exist and contain at least 1 non-empty JSONL record.
- EVERY line must be a JSON object in record format (no meta/schema-only lines).
- Required keys must be present and non-empty strings:
  ts, trace_version, decision_id, actor, phase, result
- Ledger integrity:
  - Records must be unique (no exact duplicate records) using a composite key.
  - ts must be non-decreasing across the file (monotonic).
Exit: 0 OK, 1 FAIL
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
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


def _parse_iso(ts: str, idx: int) -> datetime:
    if not isinstance(ts, str) or not ts.strip():
        fail(f"{PATH}: line {idx} ts must be a non-empty string")
    s = ts.strip()
    # Accept Z (UTC) and offsets; normalize Z -> +00:00 for fromisoformat
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        return datetime.fromisoformat(s)
    except Exception:
        fail(f"{PATH}: line {idx} ts not ISO-parseable: {ts}")
    raise AssertionError("unreachable")


def _validate_required(idx: int, obj: Dict[str, Any]) -> None:
    missing = [k for k in REQUIRED if k not in obj or obj[k] in (None, "", [])]
    if missing:
        fail(f"{PATH}: line {idx} missing required keys {missing}")

    # Type checks (strings)
    for k in REQUIRED:
        if not isinstance(obj[k], str):
            fail(f"{PATH}: line {idx} key '{k}' must be string")

    # Quick sanity: avoid accidental meta-only records
    # (We only accept record-format lines that include decision_id etc.)
    if obj.get("schema_version") is not None and "decision_id" not in obj:
        fail(
            f"{PATH}: line {idx} looks like a meta/schema record; "
            "ledger must contain record-format only"
        )

    if not obj["phase"].strip():
        fail(f"{PATH}: line {idx} phase must not be empty")


def main() -> None:
    lines = _load_lines()

    seen_records: Set[Tuple[str, str, str, str, str]] = set()
    prev_dt: datetime | None = None

    for i, ln in enumerate(lines, start=1):
        obj = _parse_obj(i, ln)
        _validate_required(i, obj)

        # Record uniqueness (NOT decision_id uniqueness!)
        rec_key = (
            obj["ts"],
            obj["trace_version"],
            obj["decision_id"],
            obj["actor"],
            obj["phase"],
        )
        if rec_key in seen_records:
            fail(f"{PATH}: duplicate record found at line {i} (key={rec_key})")
        seen_records.add(rec_key)

        # Monotonic ts (non-decreasing)
        dt = _parse_iso(obj["ts"], i)
        if prev_dt is not None and dt < prev_dt:
            fail(f"{PATH}: non-monotonic ts at line {i} ({obj['ts']} < previous)")
        prev_dt = dt

    print(
        f"VALIDATION OK: {PATH} "
        f"(checked {len(lines)} ledger records; unique record keys; monotonic ts)."
    )
    sys.exit(0)


if __name__ == "__main__":
    main()