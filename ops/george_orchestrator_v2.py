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

AUTONOMY_FILE = OPS_DIR / "autonomy.json"

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

def load_health() -> HealthState:
    """Lädt den letzten Health-Status oder liefert Defaults."""
    data = load_json(STATUS_FILE, default=None)
    if not data:
        return HealthState()
    try:
        return HealthState.from_dict(data)
    except Exception as exc:
        print(f"[GEORGE V2] Konnte HealthState nicht rekonstruieren: {exc}", file=sys.stderr)
        return HealthState()


def save_health(health: HealthState) -> None:
    """Persistiert Health-State + schreibt Logzeile."""
    data = health.to_dict()
    save_json(STATUS_FILE, data)
    append_jsonl(REPORTS_DIR / "health_log.jsonl", data)


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
# Autonomy-Konfiguration
# ---------------------------------------------------------------------------

def load_autonomy_config() -> Dict[str, Any]:
    """Lädt die Autonomie-/Capability-Map aus autonomy.json."""
    cfg = load_json(AUTONOMY_FILE, default={})
    if not isinstance(cfg, dict):
        return {}
    return cfg


def get_agent_profile(agent_id: str) -> Dict[str, Any]:
    """
    Liefert das Agent-Profil aus autonomy.json, z.B.:

    {
      "status": "active",
      "autonomy": 0.35,
      "role": "...",
      "depends_on": [...],
      "actions": [...],
      "failure_thresholds": {...}
    }
    """
    cfg = load_autonomy_config()
    agents = cfg.get("agents", {})
    profile = agents.get(agent_id, {})
    if not isinstance(profile, dict):
        return {}
    return profile



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
        """Robuste Rekonstruktion aus einem Dict."""
        return HealthState(
            agent_response_success_rate=float(
                data.get("agent_response_success_rate", 0.0)
            ),
            last_autonomous_action=data.get("last_autonomous_action"),
            self_detection_errors=int(data.get("self_detection_errors", 0)),
            system_stability_score=float(
                data.get("system_stability_score", 0.0)
            ),
            autonomy_level_estimate=float(
                data.get("autonomy_level_estimate", 0.5)
            ),
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

def save_decision(decision: Decision | Dict[str, Any]) -> None:
    """
    Persistiert eine Decision in:
    - decisions/history/YYYY-MM-DD.jsonl
    - decisions/latest.json
    - decisions/snapshots/YYYY-MM-DD.json
    """
    # Immer als Dict arbeiten
    if isinstance(decision, Decision):
        dec_dict = decision.to_dict()
    else:
        dec_dict = dict(decision)

    today = datetime.now(timezone.utc).date().isoformat()

    # 1) History-Log (append)
    history_file = DECISIONS_HISTORY_DIR / f"{today}.jsonl"
    with history_file.open("a", encoding="utf-8") as f:
        f.write(json.dumps(dec_dict, ensure_ascii=False) + "\n")

    # 2) latest.json
    with DECISIONS_LATEST.open("w", encoding="utf-8") as f:
        json.dump(dec_dict, f, indent=2, ensure_ascii=False)

    # 3) Snapshot aktualisieren
    update_snapshot(today, dec_dict)


def update_snapshot(date: str, decision: Dict[str, Any]) -> None:
    """
    Aktualisiert das Tages-Snapshot:
    - Gesamte Decisions
    - Erfolgreiche / fehlgeschlagene
    - Breakdown nach Agent
    """
    snapshot_path = DECISIONS_SNAPSHOTS_DIR / f"{date}.json"

    if snapshot_path.exists():
        try:
            with snapshot_path.open("r", encoding="utf-8") as f:
                snapshot = json.load(f)
        except json.JSONDecodeError:
            print(f"[GEORGE V2] Snapshot defekt, initialisiere neu: {snapshot_path}", file=sys.stderr)
            snapshot = {}
    else:
        snapshot = {}

    # Defaults setzen
    snapshot.setdefault("date", date)
    snapshot.setdefault("total_decisions", 0)
    snapshot.setdefault("successful", 0)
    snapshot.setdefault("failed", 0)
    snapshot.setdefault("by_agent", {})

    agent = decision.get("agent", "unknown")
    status = decision.get("status", "unknown")

    # Global Stats
    snapshot["total_decisions"] += 1
    if status == "success":
        snapshot["successful"] += 1
    elif status == "failed":
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

    snapshot["last_decision_id"] = decision.get("id")
    snapshot["last_updated"] = now_iso()

    with snapshot_path.open("w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2, ensure_ascii=False)

def load_rules() -> List[Dict[str, Any]]:
    """Lädt die GEORGE-Rules aus george_rules.yaml."""
    data = load_yaml(RULES_FILE, default={})
    if isinstance(data, dict):
        # Typische Struktur: { version: ..., rules: [...] }
        rules = data.get("rules", [])
    else:
        rules = data or []

    if not isinstance(rules, list):
        print("[GEORGE V2] Ungültiges Rules-Format in george_rules.yaml", file=sys.stderr)
        return []

    return rules

# ---------------------------------------------------------------------------
# Orchestrierung (MVP) – nutzt Events, Autonomie-Config & Health-State
# ---------------------------------------------------------------------------

def orchestrate() -> int:
    """Führt einen Orchestrierungszyklus für das letzte Event aus."""

    # 1) Not-Aus prüfen
    if emergency_lock_active():
        print("[GEORGE V2] Emergency-Lock aktiv – keine Aktionen erlaubt.")
        decision = Decision(
            id=str(uuid.uuid4()),
            timestamp=now_iso(),
            source_event_id=None,
            agent="george",
            action="emergency_lock_active",
            intent=None,
            confidence=0.0,
            status="blocked",
            guardian_flag="emergency_lock",
            error_message="System locked via emergency_lock.json",
            follow_up=None,
            result_summary="Orchestration aborted due to active emergency lock.",
        )
        save_decision(decision)
        health = load_health()
        health.register_result(success=False)
        save_health(health)
        return 1

    # 2) Letztes Event laden
    event = load_latest_event()
    if not event:
        print("[GEORGE V2] Kein Event vorhanden – nichts zu tun.")
        return 0

    print(f"[GEORGE V2] Verarbeite Event {event.id} von Agent '{event.agent}' – '{event.event}'")

    # 3) Autonomie-Profil des Zielagents laden
    agent_id = event.agent or "unknown"
    agent_profile = get_agent_profile(agent_id)
    autonomy_level = float(agent_profile.get("autonomy", 0.0))
    status = agent_profile.get("status", "unknown")

    # 4) Entscheidung vorbereiten
    decision = Decision(
        id=str(uuid.uuid4()),
        timestamp=now_iso(),
        source_event_id=event.id,
        agent=agent_id,
        action=event.event,
        intent=event.intent,
        confidence=autonomy_level,
        status="pending",
        guardian_flag=None,
        error_message=None,
        follow_up=None,
        result_summary=None,
    )

    # 5) Einfache Guardrails basierend auf Autonomie-Level
    execution_allowed = True
    guardian_reason = None

    if status != "active":
        execution_allowed = False
        guardian_reason = f"agent_status_{status}"

    elif autonomy_level < 0.3:
        # Unter 0.3 nur Simulation / Block
        execution_allowed = False
        guardian_reason = "autonomy_too_low"

    if not execution_allowed:
        decision.status = "blocked"
        decision.guardian_flag = guardian_reason
        decision.error_message = (
            f"Execution blocked by autonomy/guardian rules "
            f"(status={status}, autonomy={autonomy_level:.2f})."
        )
        decision.result_summary = "No action executed. Check autonomy.json and guardian rules."
        success = False
    else:
        # 6) (MVP) – Aktion simulieren statt echten Agentenaufruf
        decision.status = "success"
        decision.result_summary = (
            f"Simulated execution for agent '{agent_id}' "
            f"with autonomy={autonomy_level:.2f} on event '{event.event}'."
        )
        success = True

    # 7) Health-Status aktualisieren
    health = load_health()
    health.register_result(success=success)
    if success:
        health.last_autonomous_action = f"{agent_id}:{event.event}"
    save_health(health)

    # 8) Decision persistieren (history + latest + snapshots)
    save_decision(decision)

    # 9) Decision-Event anhängen (für Event-Timeline)
    decision_event = Event(
        id=str(uuid.uuid4()),
        timestamp=now_iso(),
        agent="george",
        event="decision_made",
        intent=event.intent,
        payload={
            "decision_id": decision.id,
            "target_agent": decision.agent,
            "status": decision.status,
            "guardian_flag": decision.guardian_flag,
            "autonomy_level": autonomy_level,
        },
        source_event_id=event.id,
    )
    append_events([decision_event])

    print(f"[GEORGE V2] Decision {decision.id} – status={decision.status}, success={success}")
    return 0

if __name__ == "__main__":
    sys.exit(orchestrate())
