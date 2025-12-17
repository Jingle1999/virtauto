#!/usr/bin/env python3
"""
Deploy Agent – Skeleton (Simulation Only)

Purpose:
- Consume deploy_intent
- Validate environment + approval
- Produce deploy_decision (NO side effects)

Status:
- Simulation default
- Real deploy blocked unless explicit approval
"""

from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any


DECISIONS_DIR = Path("ops/decisions")
DEPLOY_REPORT = DECISIONS_DIR / "deploy_latest.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def run(action: Dict[str, Any]) -> Dict[str, Any]:
    """
    action expected structure:
    {
      "intent": "deploy_intent",
      "environment": "production|staging",
      "mode": "simulation|real",
      "approval": false
    }
    """

    environment = action.get("environment", "unknown")
    mode = action.get("mode", "simulation")
    approval = action.get("approval", False)

    allowed = False
    reason = "simulation_only"

    if mode == "real":
        if approval is True:
            allowed = True
            reason = "explicit_human_approval"
        else:
            allowed = False
            reason = "missing_explicit_approval"

    report = {
        "timestamp": now_iso(),
        "agent": "deploy",
        "environment": environment,
        "mode": mode,
        "allowed": allowed,
        "reason": reason,
        "side_effects": "none",
        "note": "No deployment executed. Skeleton only."
    }

    DEPLOY_REPORT.parent.mkdir(parents=True, exist_ok=True)
    DEPLOY_REPORT.write_text(json.dumps(report, indent=2))

    return report


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Usage: deploy_agent.py <action.json>")
        sys.exit(1)

    action = json.loads(Path(sys.argv[1]).read_text())
    result = run(action)
    print(json.dumps(result, indent=2))
