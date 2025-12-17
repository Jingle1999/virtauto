#!/usr/bin/env python3
"""
ops/validate_status.py
Hard gate: validate system_status.json against agents/registry.yaml

Fail build if:
- files missing
- JSON invalid
- required keys missing
- agent statuses contain unknown states
- agent IDs diverge (registry vs system_status)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

try:
    import yaml  # pyyaml
except Exception as e:
    print("ERROR: PyYAML missing. Add 'pip install pyyaml' in workflow.", file=sys.stderr)
    raise

REGISTRY_FILE = Path("agents/registry.yaml")
STATUS_FILE = Path("ops/reports/system_status.json")

REQUIRED_TOP_KEYS = {"version", "generated_at", "environment", "system_state", "autonomy", "health", "agents"}

# Allowed statuses (align with agents/registry.yaml in your screenshot)
ALLOWED_AGENT_STATUSES = {"active", "mvp", "preparing", "planned", "disabled"}


def die(msg: str, code: int = 1) -> None:
    print(f"VALIDATION FAILED: {msg}", file=sys.stderr)
    raise SystemExit(code)


def load_yaml(path: Path) -> dict:
    if not path.exists():
        die(f"Missing file: {path}")
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception as e:
        die(f"Invalid YAML in {path}: {e}")
    return {}


def load_json(path: Path) -> dict:
    if not path.exists():
        die(f"Missing file: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        die(f"Invalid JSON in {path}: {e}")
    return {}


def main() -> None:
    registry = load_yaml(REGISTRY_FILE)
    status = load_json(STATUS_FILE)

    # --- Basic schema ---
    missing = REQUIRED_TOP_KEYS - set(status.keys())
    if missing:
        die(f"system_status.json missing keys: {sorted(missing)}")

    agents_reg = registry.get("agents", [])
    if not isinstance(agents_reg, list) or not agents_reg:
        die("registry.yaml: 'agents' must be a non-empty list")

    agents_status = status.get("agents", {})
    if not isinstance(agents_status, dict) or not agents_status:
        die("system_status.json: 'agents' must be a non-empty object/map")

    # --- Validate status enums & IDs ---
    reg_ids = []
    reg_statuses = {}
    for a in agents_reg:
        if not isinstance(a, dict):
            die("registry.yaml contains non-object agent entry")
        aid = a.get("id")
        if not aid:
            die("registry.yaml agent missing 'id'")
        reg_ids.append(aid)
        reg_statuses[aid] = a.get("status")

        # Ensure registry status is known
        if a.get("status") and a.get("status") not in ALLOWED_AGENT_STATUSES:
            die(f"registry.yaml agent '{aid}' has unknown status '{a.get('status')}'")

    status_ids = list(agents_status.keys())

    # Registry IDs must exist in system_status
    missing_in_status = sorted(set(reg_ids) - set(status_ids))
    if missing_in_status:
        die(f"Agents missing in system_status.json: {missing_in_status}")

    # System_status must not invent unknown agents (strict)
    extra_in_status = sorted(set(status_ids) - set(reg_ids))
    if extra_in_status:
        die(f"Extra agents in system_status.json not in registry.yaml: {extra_in_status}")

    # Validate each agent entry status
    for aid, entry in agents_status.items():
        if not isinstance(entry, dict):
            die(f"system_status.json agents['{aid}'] must be an object")
        s = entry.get("status")
        if not s:
            die(f"system_status.json agents['{aid}'] missing 'status'")
        if s not in ALLOWED_AGENT_STATUSES:
            die(f"system_status.json agents['{aid}'] has unknown status '{s}'")

    # Optional: Ensure “public claim” exists if present
    claims = status.get("claims", {})
    if claims and "public_statement" in claims and not claims["public_statement"]:
        die("claims.public_statement is empty")

    print("VALIDATION OK: registry.yaml <-> system_status.json are consistent.")


if __name__ == "__main__":
    main()
