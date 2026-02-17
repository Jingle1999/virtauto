#!/usr/bin/env python3
"""
Consistency Agent v1 (CI)

Purpose:
- Validate core "truth + governance" consistency.
- Align with PASS/BLOCK model and GitHub artifacts (no gate_result.json required).

Checks (FAIL):
1) agents/registry.yaml: each agent must include autonomy_mode + state
2) ops/reports/decision_trace.jsonl: latest entry must include required keys
3) latest decision_trace.outputs must reference ops/reports/system_status.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

try:
    import yaml  # type: ignore
except Exception:
    yaml = None

ROOT = Path(".")
REGISTRY = ROOT / "agents" / "registry.yaml"
DECISION_TRACE = ROOT / "ops" / "reports" / "decision_trace.jsonl"
SYSTEM_STATUS = ROOT / "ops" / "reports" / "system_status.json"

REQUIRED_REGISTRY_AGENT_FIELDS = ["autonomy_mode", "state"]
REQUIRED_DECISION_TRACE_FIELDS = [
    "schema_version",
    "generated_at",
    "trace_id",
    "intent",
    "inputs",
    "outputs",
    "because",
    "authority",
]

FAILURES: list[str] = []
WARNINGS: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def warn(msg: str) -> None:
    WARNINGS.append(msg)


def load_yaml(path: Path) -> dict:
    if yaml is None:
        raise RuntimeError("PyYAML not installed. Add to requirements or workflow.")
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def load_jsonl_last(path: Path) -> dict | None:
    if not path.exists():
        return None
    lines = [ln.strip() for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    if not lines:
        return None
    # last non-empty line
    try:
        return json.loads(lines[-1])
    except Exception as e:
        fail(f"CNS-TRACE-000: decision_trace.jsonl last line is not valid JSON ({path}): {e}")
        return None


def main() -> int:
    # 1) registry.yaml
    if not REGISTRY.exists():
        fail(f"CNS-REG-001: Missing {REGISTRY}")
    else:
        try:
            data = load_yaml(REGISTRY)
            agents = data.get("agents", [])
            if not isinstance(agents, list) or not agents:
                fail(f"CNS-REG-002: registry.yaml missing 'agents' list ({REGISTRY})")
            else:
                for a in agents:
                    if not isinstance(a, dict):
                        fail(f"CNS-REG-003: registry agent entry is not a dict ({REGISTRY})")
                        continue
                    aid = a.get("agent_id", "<unknown>")
                    for f in REQUIRED_REGISTRY_AGENT_FIELDS:
                        if f not in a or a.get(f) in (None, "", "unknown"):
                            fail(f"CNS-REG-007: Agent '{aid}' missing field: {f} ({REGISTRY})")
        except Exception as e:
            fail(f"CNS-REG-010: Could not parse registry.yaml ({REGISTRY}): {e}")

    # 2) decision_trace.jsonl schema
    last = load_jsonl_last(DECISION_TRACE)
    if last is None:
        fail(f"CNS-TRACE-001: Missing or empty decision_trace.jsonl ({DECISION_TRACE})")
    else:
        for k in REQUIRED_DECISION_TRACE_FIELDS:
            if k not in last:
                fail(f"CNS-TRACE-010: decision_trace entry missing key: {k} ({DECISION_TRACE})")

        # 3) outputs references canonical truth file
        outs = last.get("outputs", [])
        if isinstance(outs, list):
            if str(SYSTEM_STATUS).replace("\\", "/") not in [str(x) for x in outs]:
                fail(
                    "CNS-TRACE-020: latest decision_trace.outputs must include "
                    f"'{SYSTEM_STATUS.as_posix()}' ({DECISION_TRACE})"
                )
        else:
            fail(f"CNS-TRACE-021: decision_trace.outputs must be a list ({DECISION_TRACE})")

    # Emit results
    if WARNINGS:
        print("[WARN]")
        for w in WARNINGS:
            print(" -", w)

    if FAILURES:
        print("[FAIL] Consistency Agent v1")
        for f in FAILURES:
            print(" -", f)
        return 2

    print("[PASS] Consistency Agent v1")
    return 0


if __name__ == "__main__":
    sys.exit(main())
