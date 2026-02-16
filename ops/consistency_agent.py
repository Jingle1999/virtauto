#!/usr/bin/env python3
"""
Consistency Agent v1 (CI mode)
- Validates agents/registry.yaml required fields
- Validates ops/reports/system_status.json basic shape and registry alignment
- Validates ops/reports/decision_trace.jsonl entries contain required keys
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import yaml


REPO_ROOT = Path(".")
REGISTRY_PATH = REPO_ROOT / "agents" / "registry.yaml"
SYSTEM_STATUS_PATH = REPO_ROOT / "ops" / "reports" / "system_status.json"
DECISION_TRACE_PATH = REPO_ROOT / "ops" / "reports" / "decision_trace.jsonl"

# ===== tunables
MAX_STATUS_AGE_MIN = 60 * 24  # 24h
TRACE_TAIL_LINES = 200

REQUIRED_REGISTRY_FIELDS = ["agent_id", "state", "autonomy_mode"]
REQUIRED_TRACE_KEYS = ["schema_version", "generated_at", "trace_id", "inputs", "outputs", "because"]


def fail(msg: str) -> None:
    print(f"[FAIL] {msg}")
    raise SystemExit(2)


def warn(msg: str) -> None:
    print(f"[WARN] {msg}")


def ok(msg: str) -> None:
    print(f"[OK] {msg}")


def load_yaml(path: Path) -> dict:
    if not path.exists():
        fail(f"Missing required file: {path.as_posix()}")
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def load_json(path: Path) -> dict:
    if not path.exists():
        fail(f"Missing required file: {path.as_posix()}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        fail(f"Invalid JSON: {path.as_posix()} ({e})")


def parse_iso(ts: str) -> datetime:
    # Accept Z or offset
    try:
        if ts.endswith("Z"):
            return datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return datetime.fromisoformat(ts)
    except Exception:
        raise ValueError(f"Invalid ISO timestamp: {ts}")


def tail_lines(path: Path, n: int) -> list[str]:
    if not path.exists():
        fail(f"Missing required file: {path.as_posix()}")
    lines = path.read_text(encoding="utf-8").splitlines()
    return lines[-n:] if len(lines) > n else lines


def validate_registry() -> dict:
    reg = load_yaml(REGISTRY_PATH)
    agents = reg.get("agents", [])
    if not isinstance(agents, list) or not agents:
        fail("agents/registry.yaml must contain a non-empty 'agents:' list")

    for a in agents:
        if not isinstance(a, dict):
            fail("agents/registry.yaml: each agent entry must be a mapping")
        for f in REQUIRED_REGISTRY_FIELDS:
            if f not in a or a.get(f) in (None, "", "unknown"):
                fail(f"Agent missing field: {f} ({REGISTRY_PATH.as_posix()})")

    ok("agents/registry.yaml required fields present.")
    return reg


def validate_system_status(registry: dict) -> None:
    ss = load_json(SYSTEM_STATUS_PATH)

    for k in ["generated_at", "environment"]:
        if k not in ss or not isinstance(ss[k], str) or not ss[k].strip():
            fail(f"system_status missing/invalid key: {k} ({SYSTEM_STATUS_PATH.as_posix()})")

    try:
        gen = parse_iso(ss["generated_at"])
    except ValueError as e:
        fail(f"{e} ({SYSTEM_STATUS_PATH.as_posix()})")

    now = datetime.now(timezone.utc)
    age = now - gen.astimezone(timezone.utc)
    if age > timedelta(minutes=MAX_STATUS_AGE_MIN):
        warn(f"system_status generated_at is {age.total_seconds()/60:.1f} minutes old (max={MAX_STATUS_AGE_MIN})")

    # Align system_status agents with registry
    reg_ids = {a["agent_id"] for a in registry.get("agents", []) if isinstance(a, dict) and "agent_id" in a}
    ss_agents = ss.get("agents", [])
    if isinstance(ss_agents, list) and ss_agents:
        for a in ss_agents:
            aid = a.get("agent_id") if isinstance(a, dict) else None
            if aid and aid not in reg_ids:
                fail(f"Agent '{aid}' present in system_status but missing in agents/registry.yaml ({SYSTEM_STATUS_PATH.as_posix()})")

    ok("ops/reports/system_status.json basic checks ok.")


def validate_decision_trace() -> None:
    lines = tail_lines(DECISION_TRACE_PATH, TRACE_TAIL_LINES)
    if not lines:
        fail("ops/reports/decision_trace.jsonl is empty")

    # Validate at least one valid entry in tail
    valid = 0
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue

        missing = [k for k in REQUIRED_TRACE_KEYS if k not in obj]
        if missing:
            # Keep scanning; but count fails for visibility
            for m in missing:
                warn(f"decision_trace entry missing key: {m} ({DECISION_TRACE_PATH.as_posix()})")
            continue

        valid += 1

    if valid == 0:
        fail("No valid decision_trace entries found in tail window (last 200 lines)")

    ok("ops/reports/decision_trace.jsonl contains at least one valid entry.")


def main() -> int:
    print("[Consistency Agent v1] START")
    registry = validate_registry()
    validate_system_status(registry)
    validate_decision_trace()
    print("[Consistency Agent v1] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
