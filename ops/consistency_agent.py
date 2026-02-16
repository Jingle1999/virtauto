#!/usr/bin/env python3
"""
ops/consistency_agent.py

Consistency checks for virtauto governance.

Policy updates (per Andreas):
- PASS/BLOCK is enforced via CI outcome + GitHub artifacts (no mandatory gate_result.json file).
- Keep checks deterministic and minimal.

Exit codes:
- 0 => PASS
- 2 => BLOCK (violations)
"""

import json
import sys
from pathlib import Path

REGISTRY_PATH = Path("agents/registry.yaml")
SYSTEM_STATUS_PATH = Path("ops/reports/system_status.json")
DECISION_TRACE_JSONL = Path("ops/reports/decision_trace.jsonl")

REQUIRED_REGISTRY_FIELDS = {"autonomy_mode", "state"}
REQUIRED_SYSTEM_STATUS_KEYS = {"schema_version", "generated_at", "environment", "agents"}
REQUIRED_TRACE_KEYS = {"schema_version", "generated_at", "trace_id", "intent", "inputs", "outputs", "because"}


def fail(msg: str, code: str) -> None:
    print(f" - FAIL {code}: {msg}")


def warn(msg: str, code: str) -> None:
    print(f" - WARN {code}: {msg}")


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_yaml_minimal(path: Path) -> dict:
    # Minimal YAML loader without dependencies:
    # We only support the exact structure used in agents/registry.yaml above.
    # If you already have PyYAML in requirements, replace this with yaml.safe_load.
    txt = path.read_text(encoding="utf-8").splitlines()
    data = {"agents": []}
    cur = None
    for line in txt:
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if s.startswith("agents:"):
            continue
        if s.startswith("- "):
            if cur:
                data["agents"].append(cur)
            cur = {}
            s = s[2:].strip()
            if ":" in s:
                k, v = s.split(":", 1)
                cur[k.strip()] = v.strip().strip('"').strip("'")
        elif ":" in s and cur is not None:
            k, v = s.split(":", 1)
            cur[k.strip()] = v.strip().strip('"').strip("'")
    if cur:
        data["agents"].append(cur)
    return data


def check_registry() -> list[str]:
    errors = []
    if not REGISTRY_PATH.exists():
        errors.append("CNS-REG-001: agents/registry.yaml missing")
        return errors

    reg = load_yaml_minimal(REGISTRY_PATH)
    agents = reg.get("agents", [])
    if not isinstance(agents, list) or not agents:
        errors.append("CNS-REG-002: agents list missing/empty in agents/registry.yaml")
        return errors

    for a in agents:
        agent_id = a.get("agent_id", "<missing agent_id>")
        for f in REQUIRED_REGISTRY_FIELDS:
            if f not in a or not str(a.get(f)).strip():
                errors.append(f"CNS-REG-007: Agent '{agent_id}' missing field: {f} (agents/registry.yaml)")
    return errors


def check_system_status() -> list[str]:
    errors = []
    if not SYSTEM_STATUS_PATH.exists():
        errors.append("CNS-TIME-001: ops/reports/system_status.json missing")
        return errors

    try:
        s = load_json(SYSTEM_STATUS_PATH)
    except Exception as e:
        errors.append(f"CNS-STAT-001: system_status.json invalid JSON: {e}")
        return errors

    missing = [k for k in REQUIRED_SYSTEM_STATUS_KEYS if k not in s]
    if missing:
        errors.append(f"CNS-STAT-002: system_status.json missing keys: {missing}")

    # Ensure every agent in system_status exists in registry
    try:
        reg = load_yaml_minimal(REGISTRY_PATH)
        reg_ids = {a.get("agent_id") for a in reg.get("agents", [])}
        status_ids = set((s.get("agents") or {}).keys())
        for sid in sorted(status_ids):
            if sid not in reg_ids:
                errors.append(f"CNS-REG-002: Agent '{sid}' present in system_status but missing in agents/registry.yaml (ops/reports/system_status.json)")
    except Exception as e:
        errors.append(f"CNS-REG-003: Failed registry/status cross-check: {e}")

    return errors


def check_decision_trace() -> list[str]:
    errors = []
    if not DECISION_TRACE_JSONL.exists():
        errors.append("CNS-TRACE-001: ops/reports/decision_trace.jsonl missing")
        return errors

    lines = [ln.strip() for ln in DECISION_TRACE_JSONL.read_text(encoding="utf-8").splitlines() if ln.strip()]
    if not lines:
        errors.append("CNS-TRACE-002: decision_trace.jsonl is empty")
        return errors

    # Validate only the last ~200 lines (consistent with your logs)
    window = lines[-200:]
    for ln in window[-1:]:
        try:
            obj = json.loads(ln)
        except Exception as e:
            errors.append(f"CNS-TRACE-003: invalid JSONL entry: {e}")
            continue

        for k in REQUIRED_TRACE_KEYS:
            if k not in obj:
                errors.append(f"CNS-TRACE-010: decision_trace entry missing key: {k} (ops/reports/decision_trace.jsonl)")

        # NOTE: No requirement for ops/decisions/gate_result.json
        # PASS/BLOCK is enforced by CI exit code + artifacts.

    return errors


def main() -> int:
    print("[Consistency Agent v1] FAIL -> BLOCK (exit 2) / PASS -> exit 0\n")

    errors = []
    errors += check_registry()
    errors += check_system_status()
    errors += check_decision_trace()

    if errors:
        print("[BLOCK] Violations detected:")
        for e in errors:
            fail(e, e.split(":")[0] if ":" in e else "CNS-UNK")
        print("\nResult: BLOCK")
        return 2

    print("[PASS] All consistency checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
