#!/usr/bin/env python3
"""
Governance-Grade Validator
Stage 2 – Schema Harmonized

Rules:
- JSON must parse
- Required keys must exist
- Enum values validated via ops/schemas/system_status_vocab.json
- ALLOW/PASS requires audit trail
- Unknown top-level keys → WARN (not fail)
"""

from __future__ import annotations
import json
import sys
from pathlib import Path
from typing import Any, Dict


STATUS_PATH = Path("ops/reports/system_status.json")
VOCAB_PATH = Path("ops/schemas/system_status_vocab.json")


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------

def die(msg: str) -> None:
    print(f"VALIDATION FAILED: {msg}")
    sys.exit(1)


def warn(msg: str) -> None:
    print(f"VALIDATION WARN: {msg}")


def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        die(f"{path} not found")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        die(f"Invalid JSON in {path}: {e}")


def validate_enum(value: str, allowed: list[str], context: str):
    if value not in allowed:
        die(f"{context} '{value}' not in allowed values: {allowed}")


# ------------------------------------------------------------
# Main Validation
# ------------------------------------------------------------

def main() -> None:

    data = load_json(STATUS_PATH)
    vocab = load_json(VOCAB_PATH)

    # --------------------------------------------------------
    # Required Top-Level Keys
    # --------------------------------------------------------

    required_keys = [
        "schema_version",
        "system_state",
        "autonomy",
        "system",
        "agents"
    ]

    for key in required_keys:
        if key not in data:
            die(f"Missing required top-level key: '{key}'")

    # --------------------------------------------------------
    # Unknown Top-Level Keys → WARN
    # --------------------------------------------------------

    allowed_top_level = {
        "schema_version",
        "generated_at",
        "environment",
        "system_state",
        "autonomy",
        "system",
        "governance",
        "autonomy_model",
        "autonomy_score",
        "health",
        "agents",
        "links"
    }

    for key in data.keys():
        if key not in allowed_top_level:
            warn(f"Unknown top-level key detected: '{key}'")

    # --------------------------------------------------------
    # System State
    # --------------------------------------------------------

    validate_enum(
        data["system_state"],
        vocab["system_state"],
        "system_state"
    )

    # --------------------------------------------------------
    # System Object
    # --------------------------------------------------------

    if not isinstance(data["system"], dict):
        die("system must be an object")

    validate_enum(
        data["system"].get("state", "UNKNOWN"),
        vocab["system_state"],
        "system.state"
    )

    validate_enum(
        data["system"].get("autonomy_mode", "UNKNOWN"),
        vocab["autonomy_mode"],
        "system.autonomy_mode"
    )

    # --------------------------------------------------------
    # Top-Level Autonomy
    # --------------------------------------------------------

    validate_enum(
        data["autonomy"],
        vocab["autonomy_mode"],
        "autonomy"
    )

    # --------------------------------------------------------
    # Health
    # --------------------------------------------------------

    if "health" in data and isinstance(data["health"], dict):
        signal = data["health"].get("signal")
        if signal:
            validate_enum(
                signal,
                vocab["health_signal"],
                "health.signal"
            )

    # --------------------------------------------------------
    # Agents
    # --------------------------------------------------------

    if not isinstance(data["agents"], dict):
        die("agents must be an object")

    for name, agent in data["agents"].items():
        if not isinstance(agent, dict):
            die(f"agents.{name} must be an object")

        if "state" in agent:
            validate_enum(
                agent["state"],
                vocab["agent_state"],
                f"agents.{name}.state"
            )

        if "autonomy_mode" in agent:
            validate_enum(
                agent["autonomy_mode"],
                vocab["autonomy_mode"],
                f"agents.{name}.autonomy_mode"
            )

    # --------------------------------------------------------
    # Governance: ALLOW/PASS requires audit trail
    # --------------------------------------------------------

    gate_verdict = None

    if "autonomy_score" in data:
        gate_verdict = (
            data["autonomy_score"]
            .get("inputs", {})
            .get("gate_verdict")
        )

    if gate_verdict in {"ALLOW", "PASS"}:
        links = data.get("links", {})
        decision_trace = links.get("decision_trace")

        if not decision_trace:
            die("ALLOW/PASS requires audit trail (links.decision_trace missing)")

    print("VALIDATION OK: system_status.json is governance-grade compliant.")
    sys.exit(0)


if __name__ == "__main__":
    main()
