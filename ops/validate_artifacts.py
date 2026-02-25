#!/usr/bin/env python3
"""
Mandatory Artifact Gate (Phase 10 prep)

Fails CI if required governance/ops artifacts are missing or empty.
This is intentionally deterministic and dependency-free.

Artifacts checked (repo-relative):
- ops/contracts/george_contract_v1.md
- ops/authority_matrix.yaml
- ops/authority_graph_v1.yaml
- ops/decisions/latest.json
- ops/decisions/gate_result.json
- ops/reports/system_status.json
- ops/reports/decision_trace.jsonl
"""

from __future__ import annotations

import sys
from pathlib import Path


REQUIRED = [
    "ops/contracts/george_contract_v1.md",
    "ops/authority_matrix.yaml",
    "ops/authority_graph_v1.yaml",
    "ops/decisions/latest.json",
    "ops/decisions/gate_result.json",
    "ops/reports/system_status.json",
    "ops/reports/decision_trace.jsonl",
]


def fail(msg: str) -> None:
    print(f"ARTIFACT GATE FAILED: {msg}")
    sys.exit(1)


def warn(msg: str) -> None:
    print(f"ARTIFACT GATE WARN: {msg}")


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]

    missing = []
    empty = []

    for rel in REQUIRED:
        p = repo_root / rel
        if not p.exists():
            missing.append(rel)
            continue
        try:
            size = p.stat().st_size
        except OSError:
            missing.append(rel)
            continue
        if size <= 0:
            empty.append(rel)

    if missing or empty:
        parts = []
        if missing:
            parts.append("missing: " + ", ".join(missing))
        if empty:
            parts.append("empty: " + ", ".join(empty))
        fail(" | ".join(parts))

    # Optional soft checks (non-blocking)
    # Example: decision_trace.jsonl should contain at least one line
    trace = repo_root / "ops/reports/decision_trace.jsonl"
    try:
        if trace.exists() and trace.stat().st_size > 0:
            first_line = trace.read_text(encoding="utf-8", errors="ignore").splitlines()[:1]
            if not first_line:
                warn("decision_trace.jsonl has no readable lines (but is non-empty).")
    except Exception:
        warn("could not read decision_trace.jsonl for soft sanity check.")

    print("ARTIFACT GATE OK: required artifacts present and non-empty.")
    sys.exit(0)


if __name__ == "__main__":
    main()