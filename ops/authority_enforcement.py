from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml

MATRIX_PATH = Path("ops/policies/authority_matrix.yaml")


@dataclass
class EnforcementResult:
    allowed: bool
    level: str  # "ok" | "warn" | "block"
    reason: str


def _load_matrix() -> Dict[str, Any]:
    if not MATRIX_PATH.exists():
        return {}
    return yaml.safe_load(MATRIX_PATH.read_text(encoding="utf-8")) or {}


def enforce_authority(decision: Dict[str, Any]) -> EnforcementResult:
    """
    Expects decision fields (minimum):
      - decision_class: safety|operational|strategic|deploy
      - authority_trace: { approvals: [...], participants: [...] }  (or similar)
    """
    matrix = _load_matrix()
    enforcement = (matrix.get("enforcement") or {})
    mode = (enforcement.get("mode") or "warn").lower()
    require_trace = bool(enforcement.get("require_trace", True))
    require_human_final = bool(enforcement.get("require_human_approval_for_final", True))

    dclass = (decision.get("decision_class") or "").strip().lower()
    rules = (matrix.get("decision_classes") or {}).get(dclass) or {}

    if not rules:
        # unbekannte Klasse -> nicht blocken, aber markieren
        return EnforcementResult(True, "warn", f"Unknown decision_class '{dclass}' (no rules).")

    trace = decision.get("authority_trace")
    if require_trace and not trace:
        if mode == "block":
            return EnforcementResult(False, "block", "Missing authority_trace (required).")
        return EnforcementResult(True, "warn", "Missing authority_trace (required).")

    approvals: List[str] = []
    participants: List[str] = []
    if isinstance(trace, dict):
        approvals = [str(x).lower() for x in (trace.get("approvals") or [])]
        participants = [str(x).lower() for x in (trace.get("participants") or [])]

    required_chain: List[str] = [str(x).lower() for x in (rules.get("required_chain") or [])]
    final_authority = str(rules.get("final_authority") or "").lower()

    missing = [r for r in required_chain if (r not in participants and r not in approvals)]
    if missing:
        msg = f"Authority chain incomplete. Missing: {missing}"
        if mode == "block":
            return EnforcementResult(False, "block", msg)
        return EnforcementResult(True, "warn", msg)

    if require_human_final and final_authority == "human":
        # “human final” = human approval muss drin sein
        if "human" not in approvals:
            msg = "Human final authority required, but no human approval present."
            if mode == "block":
                return EnforcementResult(False, "block", msg)
            return EnforcementResult(True, "warn", msg)

    return EnforcementResult(True, "ok", "Authority enforcement passed.")
