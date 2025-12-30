#!/usr/bin/env python3
import json
import sys
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[0]
OPS = ROOT
SCHEMAS = OPS / "contracts" / "schemas"

SYSTEM_STATUS = OPS / "system_status.json"
LATEST = OPS / "decisions" / "latest.json"
TRACE_JSONL = OPS / "reports" / "decision_trace.jsonl"

SYSTEM_STATUS_SCHEMA = SCHEMAS / "system_status_v1.schema.json"
LATEST_SCHEMA = SCHEMAS / "decision_latest_v1.schema.json"
TRACE_RECORD_SCHEMA = SCHEMAS / "decision_trace_record_v1.schema.json"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_schema(path: Path):
    return load_json(path)


def validate_one(instance, schema, name: str):
    try:
        jsonschema.validate(instance=instance, schema=schema)
        print(f"OK: {name}")
        return True
    except Exception as e:
        print(f"FAIL: {name}: {e}", file=sys.stderr)
        return False


def main() -> int:
    ok = True

    if not SYSTEM_STATUS.exists():
        print("FAIL: ops/system_status.json missing", file=sys.stderr)
        ok = False
    else:
        ok &= validate_one(load_json(SYSTEM_STATUS), load_schema(SYSTEM_STATUS_SCHEMA), "system_status.json")

    if not LATEST.exists():
        print("FAIL: ops/decisions/latest.json missing", file=sys.stderr)
        ok = False
    else:
        ok &= validate_one(load_json(LATEST), load_schema(LATEST_SCHEMA), "decisions/latest.json")

    if not TRACE_JSONL.exists():
        print("FAIL: ops/reports/decision_trace.jsonl missing", file=sys.stderr)
        ok = False
    else:
        schema = load_schema(TRACE_RECORD_SCHEMA)
        lines = [ln for ln in TRACE_JSONL.read_text(encoding="utf-8").splitlines() if ln.strip()]
        if not lines:
            print("FAIL: decision_trace.jsonl empty", file=sys.stderr)
            ok = False
        else:
            # validate last ~50 lines (fast + enough)
            for ln in lines[-50:]:
                try:
                    rec = json.loads(ln)
                except Exception as e:
                    print(f"FAIL: decision_trace.jsonl contains invalid JSON: {e}", file=sys.stderr)
                    ok = False
                    continue
                ok &= validate_one(rec, schema, "decision_trace record")

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
