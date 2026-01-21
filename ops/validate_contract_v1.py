#!/usr/bin/env python3
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import jsonschema

ROOT = Path(__file__).resolve().parents[0]
OPS = ROOT
SCHEMAS = OPS / "contracts" / "schemas"

# Prefer canonical truth location (what your traces show as output)
SYSTEM_STATUS_PRIMARY = OPS / "reports" / "system_status.json"
SYSTEM_STATUS_LEGACY = OPS / "system_status.json"

LATEST = OPS / "decisions" / "latest.json"
TRACE_JSONL = OPS / "reports" / "decision_trace.jsonl"

SYSTEM_STATUS_SCHEMA = SCHEMAS / "system_status_v1.schema.json"
LATEST_SCHEMA = SCHEMAS / "decision_latest_v1.schema.json"
TRACE_RECORD_SCHEMA = SCHEMAS / "decision_trace_record_v1.schema.json"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_schema(path: Path) -> Dict[str, Any]:
    return load_json(path)


def validate_one(instance: Any, schema: Dict[str, Any], name: str) -> bool:
    try:
        jsonschema.validate(instance=instance, schema=schema)
        print(f"OK: {name}")
        return True
    except Exception as e:
        print(f"FAIL: {name}: {e}", file=sys.stderr)
        return False


def pick_system_status_path() -> Optional[Path]:
    if SYSTEM_STATUS_PRIMARY.exists():
        return SYSTEM_STATUS_PRIMARY
    if SYSTEM_STATUS_LEGACY.exists():
        return SYSTEM_STATUS_LEGACY
    return None


def normalize_trace_record(rec: Dict[str, Any]) -> Dict[str, Any]:
    """
    Backward-compat shim:
    - If 'ts' missing but 'generated_at' exists: use it as 'ts'
    - If 'trace_version' missing: set to 'v1' ONLY if record otherwise looks v1-like
      (schema enforces 'v1' const anyway)
    NOTE: We do NOT fabricate 'decision_id'. If it's missing, validation should fail,
    because Phase 2 requires decision trace to be linkable to a decision.
    """
    out = dict(rec)
    if "ts" not in out and "generated_at" in out:
        out["ts"] = out["generated_at"]
    if "trace_version" not in out:
        out["trace_version"] = "v1"
    return out


def read_last_jsonl_records(path: Path, max_lines: int = 50) -> Tuple[int, int]:
    """
    Returns (valid_count, invalid_count) for last max_lines non-empty lines.
    """
    schema = load_schema(TRACE_RECORD_SCHEMA)
    lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]

    if not lines:
        print("FAIL: decision_trace.jsonl empty", file=sys.stderr)
        return (0, 1)

    valid = 0
    invalid = 0

    for ln in lines[-max_lines:]:
        try:
            rec = json.loads(ln)
        except Exception as e:
            print(f"FAIL: decision_trace.jsonl contains invalid JSON: {e}", file=sys.stderr)
            invalid += 1
            continue

        if not isinstance(rec, dict):
            print("FAIL: decision_trace.jsonl record is not an object", file=sys.stderr)
            invalid += 1
            continue

        rec_norm = normalize_trace_record(rec)
        ok = validate_one(rec_norm, schema, "decision_trace record")
        if ok:
            valid += 1
        else:
            invalid += 1

    return (valid, invalid)


def main() -> int:
    ok = True

    # --- System status (Truth) ---
    status_path = pick_system_status_path()
    if status_path is None:
        print(
            "FAIL: system status missing. Expected one of:\n"
            f"  - {SYSTEM_STATUS_PRIMARY}\n"
            f"  - {SYSTEM_STATUS_LEGACY}",
            file=sys.stderr,
        )
        ok = False
    else:
        ok &= validate_one(
            load_json(status_path),
            load_schema(SYSTEM_STATUS_SCHEMA),
            f"system_status ({status_path.as_posix()})",
        )

    # --- Decision latest (Authority/Decision surface) ---
    if not LATEST.exists():
        print("FAIL: ops/decisions/latest.json missing", file=sys.stderr)
        ok = False
    else:
        # Optional: hard fail if it's clearly a placeholder/template
        latest_text = LATEST.read_text(encoding="utf-8")
        if "ISO-8601" in latest_text or '"uuid"' in latest_text:
            print(
                "FAIL: ops/decisions/latest.json looks like a placeholder/template. "
                "Populate it with real fields according to decision_latest_v1.schema.json.",
                file=sys.stderr,
            )
            ok = False
        else:
            ok &= validate_one(load_json(LATEST), load_schema(LATEST_SCHEMA), "decisions/latest.json")

    # --- Decision trace (Explainability) ---
    if not TRACE_JSONL.exists():
        print("FAIL: ops/reports/decision_trace.jsonl missing", file=sys.stderr)
        ok = False
    else:
        valid, invalid = read_last_jsonl_records(TRACE_JSONL, max_lines=50)
        if valid == 0:
            print(
                "FAIL: decision_trace.jsonl has no valid v1 records in the last 50 lines.\n"
                "Hint: records must include at least: ts, trace_version='v1', decision_id, actor, phase, result.",
                file=sys.stderr,
            )
            ok = False
        else:
            print(f"OK: decision_trace.jsonl has {valid} valid record(s) ({invalid} invalid) in last 50 lines.")

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
