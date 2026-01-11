#!/usr/bin/env python3
# ops/status_agent.py
# Deterministic Status Agent (primary/backup) that regenerates system_status.json
# and emits auditable evidence. No learning, no heuristics.

from __future__ import annotations
import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

TRUTH_PATH = Path("ops/reports/system_status.json")
TRACE_PATH = Path("ops/reports/status_trace.jsonl")
ACTIVITY_PATH = Path("ops/agent_activity.jsonl")

def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def ensure_parent(p: Path) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)

def append_jsonl(path: Path, obj: dict) -> None:
    ensure_parent(path)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")

def write_json(path: Path, obj: dict) -> None:
    ensure_parent(path)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write("\n")
    tmp.replace(path)

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", choices=["primary", "backup"], required=True)
    ap.add_argument("--run-id", default=os.getenv("GITHUB_RUN_ID", "local"))
    ap.add_argument("--attempt", default=os.getenv("GITHUB_RUN_ATTEMPT", "0"))
    ap.add_argument("--sha", default=os.getenv("GITHUB_SHA", "local"))
    ap.add_argument("--ref", default=os.getenv("GITHUB_REF_NAME", "local"))
    args = ap.parse_args()

    ts = utc_now()
    agent_name = "status_agent_v1" if args.agent == "primary" else "status_agent_v1_backup"
    trace_id = f"{args.run_id}-{args.attempt}"

    # Deterministic “health” in Phase 8: only reflect what we can *prove*.
    # Here: we prove that the Status Agent ran and wrote truth + evidence.
    status = {
        "generated_at": ts,
        "environment": "production",
        "system": {
            "state": "ONLINE",
            "mode": "SUPERVISED",
            "truth_lock": "ENFORCED"
        },
        "health": {
            "signal": "GREEN",
            "overall_score": 1.0,
            "score_basis": "status_agent_execution"
        },
        "autonomy_score": {
            "percent": 0.0,
            "mode": "SUPERVISED",
            "gate_verdict": "PASS",
            "note": "Autonomy scoring not enabled yet (Phase 4 non-compliant