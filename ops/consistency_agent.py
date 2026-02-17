#!/usr/bin/env python3
"""
consistency_agent.py (v1 minimal)

Goal (minimal):
- Ensure agents/registry.yaml exists + parses + each agent has required fields:
  - autonomy_mode
  - state
- Ensure ops/reports/decision_trace.jsonl exists, is valid JSONL, and last entry includes:
  - outputs as list
  - outputs contains "ops/reports/system_status.json"

Exit codes:
- 0 on pass
- 2 on fail (to match existing pipeline expectations)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    import yaml  # type: ignore
except Exception:
    yaml = None

REGISTRY_PATH = Path("agents/registry.yaml")
DECISION_TRACE_JSONL = Path("ops/reports/decision_trace.jsonl")
SYSTEM_STATUS = "ops/reports/system_status.json"

FAILURES: list[str] = []
WARNINGS: list[str] = []


def fail(code: str, msg: str) -> None:
    FAILURES.append(f"{code}: {msg}")


def warn(code: str, msg: str) -> None:
    WARNINGS.append(f"{code}: {msg}")


def load_yaml(path: Path) -> dict:
    if yaml is None:
        raise RuntimeError("PyYAML not available. Add pyyaml to workflow deps or vendor a minimal parser.")
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_last_jsonl_entry(path: Path) -> dict:
    lines = [ln.strip() for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    if not lines:
        raise ValueError("empty jsonl")
    return json.loads(lines[-1])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", default="ci", choices=["ci", "local"])
    _ = ap.parse_args()

    # 1) Registry
    if not REGISTRY_PATH.exists():
        fail("CNS-REG-001", f"Missing {REGISTRY_PATH}")
    else:
        try:
            reg = load_yaml(REGISTRY_PATH)
            agents = reg.get("agents")
            if not isinstance(agents, list):
                fail("CNS-REG-002", "registry.yaml missing 'agents' list")
            else:
                for a in agents:
                    if not isinstance(a, dict):
                        fail("CNS-REG-003", "registry agent entry is not a dict")
                        continue
                    aid = a.get("agent_id", "<missing>")
                    if "autonomy_mode" not in a:
                        fail("CNS-REG-010", f"Agent '{aid}' missing field: autonomy_mode")
                    if "state" not in a:
                        fail("CNS-REG-011", f"Agent '{aid}' missing field: state")
        except Exception as e:
            fail("CNS-REG-900", f"Could not parse registry.yaml: {e}")

    # 2) Decision trace JSONL
    if not DECISION_TRACE_JSONL.exists():
        fail("CNS-TRACE-001", f"Missing {DECISION_TRACE_JSONL}")
    else:
        try:
            last = load_last_jsonl_entry(DECISION_TRACE_JSONL)
            outs = last.get("outputs")
            if not isinstance(outs, list):
                fail("CNS-TRACE-020", "latest decision_trace.outputs must be a list")
            else:
                outs_str = [str(x) for x in outs]
                if SYSTEM_STATUS not in outs_str:
                    fail("CNS-TRACE-021", f"latest decision_trace.outputs must include '{SYSTEM_STATUS}'")
        except Exception as e:
            fail("CNS-TRACE-900", f"Could not parse decision_trace.jsonl: {e}")

    # Report
    for w in WARNINGS:
        print(f"[WARN] {w}")

    if FAILURES:
        print("[FAIL] Consistency Agent v1")
        for f in FAILURES:
            print(f" - {f}")
        return 2

    print("[PASS] Consistency Agent v1")
    return 0


if __name__ == "__main__":
    sys.exit(main())
