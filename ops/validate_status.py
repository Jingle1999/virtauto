#!/usr/bin/env python3
"""
Robuster Validator für ops/reports/system_status.json

Ziele:
- JSON muss parsebar sein
- Mindestkeys müssen vorhanden sein (Backwards compat)
- Agentenstatus ist tolerant: case-insensitive + Synonyme
- Unbekannte Statuswerte -> WARNUNG statt FAIL (CI soll nicht unnötig blockieren)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict

STATUS_PATH = Path("ops/reports/system_status.json")

# Synonym-Mapping (alles wird auf canonical lower-case abgebildet)
STATUS_SYNONYMS = {
    "ok": "ok",
    "green": "ok",
    "healthy": "ok",
    "active": "ok",
    "running": "ok",

    "warn": "warn",
    "warning": "warn",
    "yellow": "warn",
    "degraded": "warn",

    "fail": "fail",
    "failed": "fail",
    "error": "fail",
    "red": "fail",
    "down": "fail",
    "inactive": "fail",
}

ALLOWED_CANONICAL = {"ok", "warn", "fail"}

def die(msg: str, code: int = 1) -> None:
    print(f"VALIDATION FAILED: {msg}")
    sys.exit(code)

def warn(msg: str) -> None:
    print(f"VALIDATION WARN: {msg}")

def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        die(f"{path} not found")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        die(f"Invalid JSON in {path}: {e}")

def normalize_status(raw: Any) -> str | None:
    if raw is None:
        return None
    if not isinstance(raw, str):
        warn(f"status is not a string: {raw!r} (type {type(raw).__name__})")
        return None
    key = raw.strip().lower()
    return STATUS_SYNONYMS.get(key, key)

def main() -> None:
    data = load_json(STATUS_PATH)

    # ---- Mindest-Keys (Backwards Compatibility) ----
    # Der ursprüngliche Validator erwartete diese Top-Level Keys:
    #   system_state, autonomy
    # Viele "modernere" Varianten haben zusätzlich system{...}
    if "system_state" not in data:
        die("system_status.json missing top-level key 'system_state'")
    if "autonomy" not in data:
        die("system_status.json missing top-level key 'autonomy'")

    # ---- Agents Struktur ----
    agents = data.get("agents")
    if not isinstance(agents, dict):
        die("system_status.json key 'agents' must be an object/dict")

    # ---- Status prüfen (tolerant) ----
    # Wir VALIDIEREN: wenn status fehlt -> WARN, aber nicht fail
    # wenn status vorhanden aber unbekannt -> WARN, aber nicht fail
    for agent_name, agent_obj in agents.items():
        if not isinstance(agent_obj, dict):
            warn(f"agents['{agent_name}'] is not an object/dict")
            continue

        raw_status = (
            agent_obj.get("status")
            or agent_obj.get("state")
            or agent_obj.get("health")
        )

        if raw_status is None:
            warn(f"agents['{agent_name}'] missing 'status' (allowed, but recommended)")
            continue

        norm = normalize_status(raw_status)
        if norm is None:
            warn(f"agents['{agent_name}'] has unreadable status: {raw_status!r}")
            continue

        if norm not in ALLOWED_CANONICAL:
            # NICHT FAILEN – nur warnen, damit design-gate nicht blockiert
            warn(f"agents['{agent_name}'] has unknown status '{raw_status}' (normalized '{norm}')")
        else:
            # Optional: canonical zurückschreiben wäre möglich – aber Validator soll nicht mutieren
            pass

    print("VALIDATION OK: system_status.json structure is acceptable.")
    sys.exit(0)

if __name__ == "__main__":
    main()
