#!/usr/bin/env python3
"""
R1 — Capability Graph invalid (Phase 9)

Deterministic detector. No LLM. No heuristics.
Returns a DetectorResult-style JSON object (regression bool + metadata).

Checks (minimal, phase-9 compliant):
- file exists
- valid JSON
- determinism rule: exactly 1 primary
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional


REPO_ROOT = Path(__file__).resolve().parents[2]
CAPABILITY_GRAPH_PATH = REPO_ROOT / "governance" / "resilience" / "capability_graph.json"


@dataclass(frozen=True)
class DetectorResult:
    regression: bool
    regression_id: Optional[str]
    type: Optional[str]
    severity: Optional[str]
    details: Dict[str, Any]


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def detect_r1_capability_graph_invalid() -> DetectorResult:
    path = CAPABILITY_GRAPH_PATH

    if not path.exists():
        return DetectorResult(
            regression=True,
            regression_id="R1",
            type="CAPABILITY_GRAPH_INVALID",
            severity="blocking",
            details={"reason": "capability_graph.json missing", "path": str(path.relative_to(REPO_ROOT))},
        )

    try:
        data = _read_json(path)
    except Exception as e:
        return DetectorResult(
            regression=True,
            regression_id="R1",
            type="CAPABILITY_GRAPH_INVALID",
            severity="blocking",
            details={
                "reason": "capability_graph.json is not valid JSON",
                "error": str(e),
                "path": str(path.relative_to(REPO_ROOT)),
            },
        )

    # Determinism rule: exactly 1 primary
    primaries = 0

    if isinstance(data, dict):
        nodes = data.get("nodes")
        if isinstance(nodes, list):
            for n in nodes:
                if isinstance(n, dict) and n.get("primary") is True:
                    primaries += 1
        else:
            for _, v in data.items():
                if isinstance(v, dict) and v.get("primary") is True:
                    primaries += 1
    elif isinstance(data, list):
        for n in data:
            if isinstance(n, dict) and n.get("primary") is True:
                primaries += 1

    if primaries != 1:
        return DetectorResult(
            regression=True,
            regression_id="R1",
            type="CAPABILITY_GRAPH_INVALID",
            severity="blocking",
            details={
                "reason": "determinism rule violated (exactly 1 primary)",
                "primary_count": primaries,
                "path": str(path.relative_to(REPO_ROOT)),
            },
        )

    return DetectorResult(
        regression=False,
        regression_id=None,
        type=None,
        severity=None,
        details={"path": str(path.relative_to(REPO_ROOT)), "primary_count": primaries},
    )


if __name__ == "__main__":
    # Print machine-readable output for audit/debug
    res = detect_r1_capability_graph_invalid()
    print(
        json.dumps(
            {
                "regression": res.regression,
                "regression_id": res.regression_id,
                "type": res.type,
                "severity": res.severity,
                "details": res.details,
            },
            indent=2,
            sort_keys=True,
        )
    )
