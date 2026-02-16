#!/usr/bin/env python3
"""
ops/consistency_agent.py — Consistency Agent v1 (CI mode)

Purpose:
- Enforce schema/consistency guardrails for "declared vs operational" artifacts.
- Fail fast in CI on:
  - agents/registry.yaml missing required fields
  - decision_trace entries missing required keys
  - latest decision trace outputs not containing required truth artifacts

This file is intentionally strict and deterministic.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

try:
    import yaml  # type: ignore
except Exception:
    yaml = None


REGISTRY_PATH = Path("agents/registry.yaml")
DECISION_TRACE_JSON = Path("ops/reports/decision_trace.json")
DECISION_TRACE_JSONL = Path("ops/reports/decision_trace.jsonl")

REQUIRED_REGISTRY_FIELDS = {"id", "state", "autonomy_mode"}

REQUIRED_DECISION_TRACE_KEYS = {
    "schema_version",
    "generated_at",
    "trace_id",
    "inputs",
    "outputs",
    "because",
}

# IMPORTANT: gate_result.json is NOT required anymore (PASS/BLOCK via exit code + artifacts)
REQUIRED_LATEST_OUTPUTS = {
    "ops/reports/system_status.json",
    "ops/reports/decision_trace.json",
    "ops/reports/decision_trace.jsonl",
    "ops/agent_activity.jsonl",
}


def fail(code: str, msg: str) -> None:
    print(f"FAIL {code}: {msg}")
    raise SystemExit(2)


def warn(code: str, msg: str) -> None:
    print(f"WARN {code}: {msg}")


def load_yaml(path: Path) -> Dict[str, Any]:
    if yaml is None:
        fail("CNS-YAML-001", "PyYAML missing in CI environment. Add it to requirements or vendor minimal parser.")
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except FileNotFoundError:
        fail("CNS-REG-001", f"Missing {path}")
    except Exception as e:
        fail("CNS-REG-002", f"Cannot parse {path}: {e}")
    return {}


def validate_registry() -> None:
    doc = load_yaml(REGISTRY_PATH)
    agents = doc.get("agents", [])
    if not isinstance(agents, list) or not agents:
        fail("CNS-REG-003", f"{REGISTRY_PATH} must contain a non-empty 'agents:' list")

    for a in agents:
        if not isinstance(a, dict):
            fail("CNS-REG-004", f"Invalid agent entry (not a dict): {a}")
        missing = [k for k in REQUIRED_REGISTRY_FIELDS if k not in a or a.get(k) in (None, "")]
        if missing:
            fail("CNS-REG-007", f"Agent '{a.get('id','<unknown>')}' missing field(s): {', '.join(missing)} ({REGISTRY_PATH})")


def iter_jsonl_tail(path: Path, max_lines: int = 200) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    tail = lines[-max_lines:] if len(lines) > max_lines else lines
    out: List[Dict[str, Any]] = []
    for ln in tail:
        ln = ln.strip()
        if not ln:
            continue
        try:
            obj = json.loads(ln)
            if isinstance(obj, dict):
                out.append(obj)
        except Exception:
            # ignore malformed lines for tail scan, but we will enforce on latest trace below
            continue
    return out


def validate_decision_trace() -> None:
    # decision_trace.json (single object) must have required keys
    try:
        obj = json.loads(DECISION_TRACE_JSON.read_text(encoding="utf-8"))
    except FileNotFoundError:
        fail("CNS-TRACE-001", f"Missing {DECISION_TRACE_JSON}")
    except Exception as e:
        fail("CNS-TRACE-002", f"Cannot parse {DECISION_TRACE_JSON}: {e}")

    for k in REQUIRED_DECISION_TRACE_KEYS:
        if k not in obj:
            fail("CNS-TRACE-010", f"decision_trace entry missing key: {k} ({DECISION_TRACE_JSON})")

    outs = obj.get("outputs", [])
    if not isinstance(outs, list):
        fail("CNS-TRACE-011", f"'outputs' must be a list ({DECISION_TRACE_JSON})")

    missing_outs = sorted([p for p in REQUIRED_LATEST_OUTPUTS if p not in outs])
    if missing_outs:
        fail(
            "CNS-TRACE-003",
            f"latest decision_trace.outputs must include {missing_outs} ({DECISION_TRACE_JSON})",
        )

    # decision_trace.jsonl (tail) entries should also include required keys (best-effort strictness)
    tail = iter_jsonl_tail(DECISION_TRACE_JSONL, max_lines=200)
    if not tail:
        warn("CNS-TRACE-020", f"{DECISION_TRACE_JSONL} missing or empty (ok in early phase, but recommended).")
        return

    # Validate only the last entry strictly
    last = tail[-1]
    for k in REQUIRED_DECISION_TRACE_KEYS:
        if k not in last:
            fail("CNS-TRACE-010", f"decision_trace entry missing key: {k} ({DECISION_TRACE_JSONL})")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", default="ci", choices=["ci"], help="run mode")
    _ = ap.parse_args()

    validate_registry()
    validate_decision_trace()

    print("OK: Consistency Agent v1 passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
