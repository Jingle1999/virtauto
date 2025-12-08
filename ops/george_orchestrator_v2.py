#!/usr/bin/env python3
"""
GEORGE Orchestrator V2 – Autonomous Edition

Ziele:
- Aus eingehenden Events echte Entscheidungen machen (Decisions)
- Guardian-Checks vor und nach der Ausführung
- Agenten-Aktionen ausführen (oder simulieren, falls kein Adapter vorhanden)
- Persistenzschicht für Decisions + Health-Metriken + Events
- Basis für 60–70 % Autonomie (Self-Healing & Guardrails ready)

V1 (george_orchestrator.py) bleibt bestehen. V2 ist bewusst modular
und kann parallel getestet werden.
"""

from __future__ import annotations

import json
import math
import os
import sys
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml as PYYAML  # PyYAML

# ---------------------------------------------------------------------------
# Pfade relativ zum Repo
# ---------------------------------------------------------------------------

OPS_DIR = Path(__file__).resolve().parent
ROOT_DIR = OPS_DIR.parents[0]

EVENTS_FILE = OPS_DIR / "events.json"
EVENT_SCHEMA_FILE = OPS_DIR / "event.schema.json"

RULES_FILE = OPS_DIR / "rules" / "george_rules.yaml"
GUARDIAN_FILE = OPS_DIR / "guardian.yaml"
GEORGE_CONFIG_FILE = OPS_DIR / "george.json"
EMERGENCY_LOCK_FILE = OPS_DIR / "emergency_lock.json"

STATUS_FILE = OPS_DIR / "status.json"
REPORTS_DIR = OPS_DIR / "reports"
DECISIONS_LOG = REPORTS_DIR / "george_decisions.jsonl"

REPORTS_DIR.mkdir(exist_ok=True, parents=True)

DECISIONS_DIR = OPS_DIR / "decisions"
DECISIONS_DIR.mkdir(exist_ok=True, parents=True)

DECISIONS_HISTORY_DIR = DECISIONS_DIR / "history"
DECISIONS_HISTORY_DIR.mkdir(exist_ok=True, parents=True)

DECISIONS_SNAPSHOTS_DIR = DECISIONS_DIR / "snapshots"
DECISIONS_SNAPSHOTS_DIR.mkdir(exist_ok=True, parents=True)

DECISIONS_LATEST = DECISIONS_DIR / "latest.json"


# ---------------------------------------------------------------------------
# Utility-Funktionen
# ---------------------------------------------------------------------------

def now_iso() -> str:
    """UTC-Zeitstempel im ISO-Format."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        print(f"[WARN] Konnte JSON nicht laden: {path} – verwende Default.", file=sys.stderr)
        return default


def save_json(path: Path, data: Any) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def append_jsonl(path: Path, record: Dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def load_yaml(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as f:
        return PYYAML.safe_load(f) or default


def emergency_lock_active() -> bool:
    cfg = load_json(EMERGENCY_LOCK_FILE, {})
    return bool(cfg.get("locked", False))


# ---------------------------------------------------------------------------
# Datenmodelle
# ---------------------------------------------------------------------------

@dataclass
class Event:
    """Eingehende/ausgehende Events (kompatibel zu V1, aber erweitert)."""
    id: str
    timestamp: str
    agent: str
    event: str
    intent: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None
    source_event_id: Optional[str] = None

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Event":
        return Event(
            id=data.get("id") or str(uuid.uuid4()),
            timestamp=data.get("timestamp") or now_iso(),
            agent=data.get("agent", "unknown"),
            event=data.get("event", "unknown"),
            intent=data.get("intent"),
            payload=data.get("payload") or {},
            source_event_id=data.get("source_event_id"),
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Decision:
    """GEORGE-Entscheidungen mit Persistenz und Guardian-Hooks."""
    id: str
    timestamp: str
    source_event_id: Optional[str]
    agent: str                # Ziel-Agent
    action: str
    intent: Optional[str]
    confidence: float
    status: str               # pending | success | error | blocked
    error_message: Optional[str] = None
    guardian_flag: Optional[str] = None
    follow_up: Optional[str] = None
    result_summary: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class HealthState:
    """Health- & Autonomie-Metriken (MVP)."""
    agent_response_success_rate: float = 0.0
    last_autonomous_action: Optional[str] = None
    self_detection_errors: int = 0
    system_stability_score: float = 0.0
    autonomy_level_estimate: float = 0.5
    total_actions: int = 0
    failed_actions: int = 0

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "HealthState":
        return HealthState(
            agent_response_success_rate=float(data.get("agent_response_success_rate", 0.0)),
            last_autonomous_action=data.get("last_autonomous_action"),
            self_detection_errors=int(data.get("self_detection_errors", 0)),
            system_stability_score=float(data.get("system_stability_score", 0.0)),
            autonomy_level_estimate=float(data.get("autonomy_level_estimate", 0.5)),
            total_actions=int(data.get("total_actions", 0)),
            failed_actions=int(data.get("failed_actions", 0)),
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def register_result(self, success: bool) -> None:
        self.total_actions += 1
        if not success:
            self.failed_actions += 1
            self.self_detection_errors += 1

        if self.total_actions > 0:
            self.agent_response_success_rate = (
                (self.total_actions - self.failed_actions) / self.total_actions
            )

        # Simple Heuristik für Systemstabilität & Autonomie
        self.system_stability_score = max(
            0.0,
            min(1.0, self.agent_response_success_rate * (1.0 - 0.1 * self.self_detection_errors)),
        )
        # Autonomie grob an Stabilität koppeln
        self.autonomy_level_estimate = max(
            0.0,
            min(1.0, 0.4 + 0.6 * self.system_stability_score),
        )


# ---------------------------------------------------------------------------
# Loading latest event & rules
# ---------------------------------------------------------------------------

def load_latest_event() -> Optional[Event]:
    """Liest das letzte Event aus events.json (Array)."""
    if not EVENTS_FILE.exists():
        print("[GEORGE V2] Keine events.json gefunden.")
        return None

    try:
        data = load_json(EVENTS_FILE, [])
        if not isinstance(data, list) or not data:
            print("[GEORGE V2] events.json ist leer.")
            return None
        latest_raw = data[-1]
        return Event.from_dict(latest_raw)
    except Exception as exc:
        print(f"[GEORGE V2] Fehler beim Laden von events.json: {exc}", file=sys.stderr)
        return None


def append_events(new_events: List[Event]) -> None:
    """Hängt Events an events.json an (Array-Append)."""
    existing = load_json(EVENTS_FILE, [])
    if not isinstance(existing, list):
        existing = []
    existing.extend(ev.to_dict() for ev in new_events)
    save_json(EVENTS_FILE, existing)

def save_decision(decision: dict):
    today = datetime.date.today().isoformat()

    # 1) Append to history log
    history_file = os.path.join(BASE, "history", f"{today}.jsonl")
    with open(history_file, "a") as f:
        f.write(json.dumps(decision) + "\n")

    # 2) Save latest.json
    latest_file = os.path.join(BASE, "latest.json")
    with open(latest_file, "w") as f:
        json.dump(decision, f, indent=2)

    # 3) Update or create snapshot
    update_snapshot(today, decision)

def update_snapshot(date: str, decision: dict):
    snapshot_path = os.path.join(BASE, "snapshots", f"{date}.json")

    # Neues Snapshot?
    if not os.path.exists(snapshot_path):
        snapshot = {
            "date": date,
            "total_decisions": 0,
            "successful": 0,
            "failed": 0,
            "by_agent": {},
            "last_decision_id": None,
            "last_updated": None
        }
    else:
        with open(snapshot_path) as f:
            snapshot = json.load(f)

    agent = decision["agent"]
    status = decision["status"]

    # Global Stats
    snapshot["total_decisions"] += 1
    if status == "success":
        snapshot["successful"] += 1
    if status == "failed":
        snapshot["failed"] += 1

    # Agent Stats
    if agent not in snapshot["by_agent"]:
        snapshot["by_agent"][agent] = {"total": 0, "success": 0, "error": 0, "blocked": 0}

    snapshot["by_agent"][agent]["total"] += 1
    if status == "success":
        snapshot["by_agent"][agent]["success"] += 1
    elif status == "failed":
        snapshot["by_agent"][agent]["error"] += 1
    elif status == "blocked":
        snapshot["by_agent"][agent]["blocked"] += 1

    snapshot["last_decision_id"] = decision["id"]
    snapshot["last_updated"] = datetime.datetime.utcnow().isoformat()

    with open(snapshot_path, "w") as f:
        json.dump(snapshot, f, indent=2)

def load_rules() -> List[Dict[str, Any]]:
    """Lädt g
