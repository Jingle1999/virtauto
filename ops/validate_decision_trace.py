#!/usr/bin/env python3
"""
validate_decision_trace.py

Phase 2 enforcement (Explainability v1):
- No PR should pass governance checks without a valid decision trace.
- Accepts:
  - ops/reports/decision_trace.jsonl (preferred)
  - ops/reports/decision_trace.json  (fallback)
- Deterministic, minimal deps (std-lib only).
- Designed to be used as a required GitHub Actions check.

Rules (minimal but meaningful):
1) At least one of the trace files must exist.
2) Trace must be non-empty.
3) Trace records must be valid JSON objects.
4) Records must contain required keys (minimal schema).
5) timestamp must look like ISO-8601 (Z or offset). (strict-enough, no external parser)

Exit codes:
- 0 OK
- 1 FAIL (blocking)
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


REPO_ROOT = Path(__file__).resolve().parents[0]  # ops/
REPO_ROOT = REPO_ROOT.parent

TRACE_JSONL = REPO_ROOT / "ops" / "reports" / "decision_trace.jsonl"
TRACE_JSON = REPO_ROOT / "ops" / "reports" / "decision_trace.json"

# Minimal required fields for "decision trace" compliance
REQUIRED_KEYS = {
    "decision_type",
    "timestamp",
    "authority",
    "action",
    "result",
    "details",
}

# ISO-ish timestamp: 2026-01-20T10:11:18Z or with offset
TS_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})$")


def fail(msg: str) -> int:
    print(f"VALIDATION FAILED: {msg}")
    return 1


def warn(msg: str) -> None:
    print(f"VALIDATION WARN: {msg}")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def parse_jsonl(text: str, max_lines: int = 200) -> List[Dict[str, Any]]:
    """
    Parse JSONL and return the last `max_lines` non-empty JSON objects.
    Fails if any parsed record is not a dict or invalid JSON.
    """
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        return []

    tail = lines[-max_lines:]
    out: List[Dict[str, Any]] = []
    for i, ln in enumerate(tail, start=max(1, len(lines) - len(tail) + 1)):
        try:
            obj = json.loads(ln)
        except Exception as e:
            raise ValueError(f"Invalid JSON on line {i}: {e}") from e
        if not isinstance(obj, dict):
            raise ValueError(f"JSONL record on line {i} is not an object/dict")
        out.append(obj)
    return out


def parse_json(text: str) -> Any:
    return json.loads(text)


def validate_record(obj: Dict[str, Any]) -> Optional[str]:
    missing = [k for k in REQUIRED_KEYS if k not in obj]
    if missing:
        return f"Missing required keys: {missing}"

    ts = obj.get("timestamp")
    if not isinstance(ts, str) or not TS_RE.match(ts):
        return f"Invalid timestamp format: {ts!r}"

    # details must be an object (we don't enforce its internal schema here)
    details = obj.get("details")
    if not isinstance(details, dict):
        return "Field 'details' must be an object/dict"

    # recommended: decision_type should be string
    if not isinstance(obj.get("decision_type"), str):
        return "Field 'decision_type' must be a string"

    return None


def select_trace_file() -> Tuple[Path, str]:
    """
    Select preferred trace file, fallback if needed.
    Returns (path, mode) where mode is 'jsonl' or 'json'.
    """
    if TRACE_JSONL.exists():
        return TRACE_JSONL, "jsonl"
    if TRACE_JSON.exists():
        return TRACE_JSON, "json"
    return TRACE_JSONL, "missing"  # default for error message


def main() -> int:
    path, mode = select_trace_file()

    if mode == "missing":
        return fail(
            "No decision trace found. Expected one of:\n"
            f"- {TRACE_JSONL.as_posix()}\n"
            f"- {TRACE_JSON.as_posix()}"
        )

    text = read_text(path).strip()
    if not text:
        return fail(f"Decision trace exists but is empty: {path.as_posix()}")

    # Validate depending on format
    try:
        if mode == "jsonl":
            records = parse_jsonl(text, max_lines=200)
            if not records:
                return fail(f"Decision trace JSONL contains no records: {path.as_posix()}")

            # Validate each record in the tail (cheap + robust)
            for idx, rec in enumerate(records[-50:], start=max(1, len(records) - 50 + 1)):
                err = validate_record(rec)
                if err:
                    return fail(f"Invalid decision trace record (tail idx={idx}): {err}")

            print(f"OK: decision_trace.jsonl valid ({len(records)} records checked in tail window).")
            return 0

        # mode == "json"
        obj = parse_json(text)
        # accept single dict or list of dicts
        if isinstance(obj, dict):
            err = validate_record(obj)
            if err:
                return fail(f"Invalid decision trace JSON object: {err}")
            print("OK: decision_trace.json valid (single object).")
            return 0

        if isinstance(obj, list):
            if not obj:
                return fail("decision_trace.json is an empty list.")
            # validate last up to 50 entries
            tail = obj[-50:]
            for i, rec in enumerate(tail, start=max(1, len(obj) - len(tail) + 1)):
                if not isinstance(rec, dict):
                    return fail(f"decision_trace.json entry idx={i} is not an object/dict")
                err = validate_record(rec)
                if err:
                    return fail(f"Invalid decision trace record idx={i}: {err}")
            print(f"OK: decision_trace.json valid (list, checked tail {len(tail)}).")
            return 0

        return fail("decision_trace.json must be an object or list of objects.")

    except Exception as e:
        return fail(f"Exception while validating {path.as_posix()}: {e}")

    # unreachable
    # return 0


if __name__ == "__main__":
    sys.exit(main())
