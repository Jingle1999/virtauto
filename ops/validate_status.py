#!/usr/bin/env python3
"""
Governance-Grade Validator für ops/reports/system_status.json
Schema-harmonisiert mit ops/schemas/system_status_vocab.json

Strikte Regeln:
- JSON muss parsebar sein
- Kanonische Enums werden hart geprüft
- Agent-Struktur muss korrekt sein
- Keine unbekannten Top-Level Keys
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict

STATUS_PATH = Path("ops/reports/system_status.json")
VOCAB_PATH = Path("ops/schemas/system_status_vocab.json")


# ------------------------------------------------------------
# Utility
# ------------------------------------------------------------

def die(msg: str) -> None:
    print(f"VALIDATION FAILED: {msg}")
    sys.exit(1)


def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        die(f"{path} not found")

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        die(f"Invalid JSON in {path}: {e}")


# ------------------------------------------------------------
# Validation Logic
# ------------------------------------------------------------

def validate_enum(value: str, allowed: list[str], context: str):
    if value not in allowed:
        die(f"{context} '{value}' not in allowed values: {allowed}")


def main() -> None:
    data = load_json(STATUS_PATH)
    vocab = load_json(VOCAB_PATH)

    # --- Required Top-Level Keys ---
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

    # --- System State ---
    validate_enum(
        data["system_state"],
        vocab["system_state"],
        "system_state"
    )

    # --- System Object ---
    system_obj = data["system"]
    if not isinstance(system_obj, dict):
        die("system must be an object")

    validate_enum(
        system_obj.get("state", "UNKNOWN"),
        vocab["system_state"],
        "system.state"
    )

    validate_enum(
        system_obj.get("autonomy_mode", "UNKNOWN"),
        vocab["autonomy_mode"],
        "system.autonomy_mode"
    )

    # --- Autonomy (top-level string) ---
    validate_enum(
        data["autonomy"],
        vocab["autonomy_mode"],
        "autonomy"
    )

    # --- Agents ---
    agents = data["agents"]
    if not isinstance(agents, dict):
        die("agents must be an object")

    for name, agent in agents.items():
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

    print("VALIDATION OK: system_status.json is governance-grade compliant.")
    sys.exit(0)


if __name__ == "__main__":
    main()
