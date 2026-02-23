#!/usr/bin/env python3
"""
Decision Trace Ledger Validator (Append-only, Record-format)

Validates ops/reports/decision_trace.jsonl as an append-only ledger where EACH line is a trace record.

Hard rules (ledger integrity):
- File must exist and contain at least 1 non-empty JSONL record.
- EVERY line must be a JSON object in record format (no meta/schema lines).
- Required keys must be present and non-empty:
  ts, trace_version, decision_id, actor, phase, result, record_id
- record_id MUST be a sha256 hex digest (64 lowercase hex chars recommended).
- record_id MUST be unique across the whole ledger.
- record_id MUST match the computed sha256 of the canonical JSON record with record_id excluded.
- ts MUST be a string and MUST NOT go backwards (monotonic non-decreasing), assuming consistent ISO8601 format.

Exit: 0 OK, 1 FAIL
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple


PATH = Path("ops/reports/decision_trace.jsonl")

# Minimal required record fields (ledger record format)
REQUIRED: Tuple[str, ...] = (
    "ts",
    "trace_version",
    "decision_id",
    "actor",
    "phase",
    "result",
    "record_id",
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

    # Quick sanity: avoid accidental meta/schema records in the ledger
    # (meta lines often have schema_version/generated_at without decision_id etc.)
    if obj.get("schema_version") is not None and "decision_id" not in obj:
        fail(f"{PATH}: line {idx} looks like a meta/schema record; ledger must contain record-format only")

    return obj


def _validate_required(idx: int, obj: Dict[str, Any]) -> None:
    missing = [k for k in REQUIRED if k not in obj or obj[k] in (None, "", [])]
    if missing:
        fail(f"{PATH}: line {idx} missing required keys {missing}")

    # Type checks for required fields
    for k in REQUIRED:
        if not isinstance(obj[k], str):
            fail(f"{PATH}: line {idx} key '{k}' must be string")

    # Basic sanity: phase must not be empty/whitespace
    if not obj["phase"].strip():
        fail(f"{PATH}: line {idx} phase must not be empty")


def _is_hex64(s: str) -> bool:
    if len(s) != 64:
        return False
    try:
        int(s, 16)
        return True
    except Exception:
        return False


def _canonical_bytes_without_record_id(obj: Dict[str, Any]) -> bytes:
    # Create a shallow copy and drop record_id to compute deterministic hash.
    tmp = dict(obj)
    tmp.pop("record_id", None)

    # Deterministic canonical JSON (sorted keys, no whitespace)
    canonical = json.dumps(tmp, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return canonical.encode("utf-8")


def _compute_record_id(obj: Dict[str, Any]) -> str:
    payload = _canonical_bytes_without_record_id(obj)
    return hashlib.sha256(payload).hexdigest()


def main() -> None:
    lines = _load_lines()

    seen_record_ids: Set[str] = set()
    prev_ts: str | None = None

    for i, ln in enumerate(lines, start=1):
        obj = _parse_obj(i, ln)
        _validate_required(i, obj)

        # Monotonic ts (string compare works for consistent ISO8601 like '...Z' or '+00:00')
        ts = obj["ts"]
        if prev_ts is not None and ts < prev_ts:
            fail(f"{PATH}: non-monotonic ts at line {i} (ts={ts} < prev_ts={prev_ts})")
        prev_ts = ts

        record_id = obj["record_id"]

        # Enforce sha256 hex digest (ledger-grade, deterministic)
        if not _is_hex64(record_id):
            fail(f"{PATH}: line {i} invalid record_id (expected 64-char hex sha256), got '{record_id}'")

        if record_id in seen_record_ids:
            fail(f"{PATH}: duplicate record_id '{record_id}' found (line {i})")
        seen_record_ids.add(record_id)

        expected = _compute_record_id(obj)
        if record_id != expected:
            fail(
                f"{PATH}: line {i} record_id mismatch. "
                f"expected={expected} got={record_id}"
            )

    print(
        f"VALIDATION OK: {PATH} "
        f"(checked {len(lines)} ledger records; record_id unique+verified; monotonic ts)."
    )
    sys.exit(0)


if __name__ == "__main__":
    main()