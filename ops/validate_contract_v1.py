#!/usr/bin/env python3
"""Validate virtauto governance contracts (v1).

This script is used as a *merge gate* for governed artifacts.

What it does:
- Validates canonical truth artifacts against their JSON Schemas
- Validates GEORGE Contract JSON against its schema
- Enforces a minimal set of GEORGE Contract hard rules that are objectively checkable in CI
  (denylist, allowlist, and mode-based apply restriction)

If any check fails: exit code 1 (merge blocked).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, Tuple
import fnmatch

import jsonschema


OPS = Path(__file__).resolve().parent
REPO = OPS.parent

SYSTEM_STATUS_PRIMARY = OPS / "reports" / "system_status.json"
DECISION_LATEST = OPS / "decisions" / "latest.json"
DECISION_TRACE = OPS / "reports" / "decision_trace.jsonl"

# Legacy (non-authoritative, allowed to exist)
SYSTEM_STATUS_LEGACY = OPS / "status.json"

SCHEMA_SYSTEM_STATUS = OPS / "contracts" / "schemas" / "system_status_v1.schema.json"
SCHEMA_DECISION_LATEST = OPS / "contracts" / "schemas" / "decision_latest_v1.schema.json"
SCHEMA_DECISION_TRACE_RECORD = OPS / "contracts" / "schemas" / "decision_trace_record_v1.schema.json"

GEORGE_CONTRACT = OPS / "contracts" / "george_contract_v1.json"
SCHEMA_GEORGE_CONTRACT = OPS / "contracts" / "schemas" / "george_contract_v1.schema.json"


def die(msg: str) -> None:
    print(f"❌ CONTRACT FAIL: {msg}", file=sys.stderr)
    raise SystemExit(1)


def load_json(path: Path) -> Any:
    if not path.exists():
        die(f"Missing required file: {path.as_posix()}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        die(f"Invalid JSON in {path.as_posix()}: {e}")


def validate_json(instance_path: Path, schema_path: Path) -> Any:
    instance = load_json(instance_path)
    schema = load_json(schema_path)
    try:
        jsonschema.validate(instance=instance, schema=schema)
    except jsonschema.ValidationError as e:
        die(f"Schema validation failed for {instance_path.as_posix()} against {schema_path.name}: {e.message}")
    return instance


def validate_decision_trace_stream(trace_path: Path, schema_path: Path) -> None:
    if not trace_path.exists():
        die(f"Missing decision trace stream: {trace_path.as_posix()}")

    schema = load_json(schema_path)

    # Validate each non-empty line as a standalone JSON object
    bad_lines = 0
    for i, line in enumerate(trace_path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except Exception as e:
            die(f"Decision trace line {i} is not valid JSON: {e}")
        try:
            jsonschema.validate(instance=rec, schema=schema)
        except jsonschema.ValidationError as e:
            bad_lines += 1
            die(f"Decision trace line {i} schema violation: {e.message}")

    if bad_lines == 0:
        print(f"✅ Decision trace stream valid: {trace_path.as_posix()}")


def _match_pattern(value: str, pattern: str) -> bool:
    # Case-insensitive glob-style match
    return fnmatch.fnmatch(value.casefold(), pattern.casefold())


def enforce_george_contract(decision_latest: Dict[str, Any]) -> None:
    """Enforce contract rules that are checkable at merge time."""
    contract = validate_json(GEORGE_CONTRACT, SCHEMA_GEORGE_CONTRACT)

    action = str(decision_latest.get("action", "")).strip()
    status = str(decision_latest.get("status", "")).strip()

    if not action:
        die("Decision latest has no 'action' field (cannot enforce GEORGE Contract).")

    # 1) Denylist: hard-stop for applied actions (status=success).
    # In HUMAN_GUARDED, proposals may still exist (e.g., deploy requests) but must remain blocked/pending.
    if status == "success":
        for entry in contract["action_policy"]["denylist"]:
            if _match_pattern(action, entry["pattern"]):
                die(f"Action '{action}' is denied by GEORGE Contract (pattern '{entry['pattern']}'): {entry['reason']}")

    # 2) Mode-based apply restriction (default_mode until runtime mode file exists)
    mode = contract["default_mode"]
    mode_cfg = contract["modes"][mode]
    can_apply = bool(mode_cfg["can_apply"])

    if status == "success" and not can_apply:
        die(
            f"Decision status=success but GEORGE Contract default_mode={mode} forbids apply "
            f"(can_apply=false). In HUMAN_GUARDED, applied state must only occur via human-approved PR merge."
        )

    # 3) In modes that allow apply, success must be allowlisted
    if status == "success" and can_apply:
        allow_actions = {a["action_id"].casefold() for a in contract["action_policy"]["allowlist"]}
        if action.casefold() not in allow_actions:
            die(f"Action '{action}' is not allowlisted for apply in mode {mode}.")

    print(f"✅ GEORGE Contract enforcement passed (mode={mode}, action={action}, status={status}).")


def main() -> int:
    # Canonical truth must exist and validate
    system_status = validate_json(SYSTEM_STATUS_PRIMARY, SCHEMA_SYSTEM_STATUS)
    decision_latest = validate_json(DECISION_LATEST, SCHEMA_DECISION_LATEST)

    # Decision trace is a stream of JSON objects (JSONL)
    validate_decision_trace_stream(DECISION_TRACE, SCHEMA_DECISION_TRACE_RECORD)

    # GEORGE Contract must exist and be self-validating; enforce minimal hard rules
    enforce_george_contract(decision_latest)

    # Legacy file is allowed but non-authoritative (no schema enforcement required)
    if SYSTEM_STATUS_LEGACY.exists():
        print(f"ℹ️ Legacy file present (non-authoritative): {SYSTEM_STATUS_LEGACY.as_posix()}")

    print("✅ All governance contract checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
