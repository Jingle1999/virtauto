#!/usr/bin/env python3
"""
Decision Trace Ledger Validator (Append-only, Record-format)

Validates ops/reports/decision_trace.jsonl as an append-only ledger where EACH line is
a trace record (JSON object).

Hard rules:
- File must exist and contain at least 1 non-empty JSONL record.
- EVERY line must be a JSON object in record format (no meta/schema lines).
- Required keys must be present and non-empty:
    ts, trace_version, decision_id, actor, phase, result
- record_id is the ledger identity per line:
    - if present: must be a string and unique across the file
    - if missing: a deterministic SHA256 hash will be computed from the record content
- ts must be a string and must NOT go backwards (monotonic non-decreasing).

Exit: 0 OK, 1 FAIL
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

PATH = Path("ops/reports/decision_trace.jsonl")

REQUIRED: Tuple[str, ...] = ("ts", "trace_version", "decision_id", "actor", "phase", "result")
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")


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

    # type checks for required fields
    for k in REQUIRED:
        if not isinstance(obj[k], str):
            fail(f"{PATH}: line {idx} key '{k}' must be string")

    # quick sanity: block meta/schema records (these are NOT trace records)
    # (We explicitly forbid 'schema_version' + missing decision_id in trace ledger.)
    if obj.get("schema_version") is not None and "decision_id" not in obj:
        fail(f"{PATH}: line {idx} looks like a meta/schema record; ledger must contain record-format only")


def _canonical_bytes_without_record_id(obj: Dict[str, Any]) -> bytes:
    # Deterministic hash basis:
    # - remove record_id if present
    # - canonical JSON (sorted keys, compact)
    payload = dict(obj)
    payload.pop("record_id", None)
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _get_or_compute_record_id(idx: int, obj: Dict[str, Any]) -> str:
    rid = obj.get("record_id")
    if rid is None or rid == "":
        # Backward-compatible: compute deterministic record_id
        h = hashlib.sha256(_canonical_bytes_without_record_id(obj)).hexdigest()
        return h

    if not isinstance(rid, str):
        fail(f"{PATH}: line {idx} record_id must be string")

    # accept UUIDs OR sha256 hex; but strongly prefer sha256 (64 hex)
    # If you want UUID-only, tighten here.
    if HEX64_RE.match(rid):
        return rid

    # very permissive UUID check (optional)
    # If you want strict UUID: tighten regex accordingly.
    if len(rid) >= 16:
        return rid

    fail(f"{PATH}: line {idx} record_id has invalid format: '{rid}'")
    return rid  # unreachable


def main() -> None:
    lines = _load_lines()

    seen_record_ids: Set[str] = set()
    prev_ts: str | None = None

    for i, ln in enumerate(lines, start=1):
        obj = _parse_obj(i, ln)
        _validate_required(i, obj)

        record_id = _get_or_compute_record_id(i, obj)
        if record_id in seen_record_ids:
            fail(f"{PATH}: duplicate record_id '{record_id}' found (line {i})")
        seen_record_ids.add(record_id)

        ts = obj["ts"]
        # monotonic (string compare works for consistent ISO8601 'Z' timestamps)
        if prev_ts is not None and ts < prev_ts:
            fail(f"{PATH}: non-monotonic ts at line {i} (ts={ts} < prev_ts={prev_ts})")
        prev_ts = ts

    print(
        f"VALIDATION OK: {PATH} (checked {len(lines)} ledger records, "
        f"unique record_id, monotonic ts)."
    )
    sys.exit(0)


if __name__ == "__main__":
    main()