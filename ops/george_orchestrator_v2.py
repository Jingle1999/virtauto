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
from typing import Any, Dict, List, Optional, Tuple

import yaml as PYYAML  # PyYAML

# ---------------------------------------------------------------------------
# Pfade relativ zum Repo
# ---------------------------------------------------------------------------

OPS_DIR = Path(__file__).resolve().parent
ROOT_DIR = OPS_DIR.parents[0]

EVENTS_FILE = OPS_DIR / "events.jsonl"
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
    """Liest das letzte Event aus events.jsonl (eine JSON-Zeile pro Event)."""
    if not EVENTS_FILE.exists():
        print("[GEORGE V2] Keine events.jsonl gefunden.")
        return None

    last = None
    with EVENTS_FILE.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                last = line
    if not last:
        print("[GEORGE V2] events.jsonl ist leer.")
        return None

    try:
        return Event.from_dict(json.loads(last))
    except Exception as exc:
        print(f"[GEORGE V2] Fehler beim Laden letztes JSONL-Event: {exc}", file=sys.stderr)
        return None


def append_events(new_events: List[Event]) -> None:
    """Hängt Events an events.jsonl an."""
    with EVENTS_FILE.open("a", encoding="utf-8") as f:
        for ev in new_events:
            f.write(json.dumps(ev.to_dict(), ensure_ascii=False) + "\n")


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
# Orchestrierungs-Helfer
# ---------------------------------------------------------------------------

def match_rule_for_event(event: "Event", rules: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Findet die erste passende Regel aus george_rules.yaml für das Event.
    Matching ist bewusst tolerant: wenn Felder in 'when' fehlen, werden sie ignoriert.
    """
    if not rules:
        return None

    for rule in rules:
        when = rule.get("when", {}) or {}
        # Unterstützte Keys (optional): agent, event, intent, source
        agent_match = when.get("agent")
        if agent_match and agent_match != event.agent:
            continue

        event_match = when.get("event")
        if event_match and event_match != event.event:
            continue

        intent_match = when.get("intent")
        if intent_match and intent_match != (event.intent or ""):
            continue

        source_match = when.get("source_event_id")
        if source_match and source_match != (event.source_event_id or ""):
            continue

        if rule:
            if "then" in rule:
                then_cfg = rule.get("then", {}) or {}
                target_agent = then_cfg.get("agent") or event.agent
                action = then_cfg.get("action") or event.event
                confidence = float(then_cfg.get("confidence", 0.8))
        else:
            # V1 action format
            act = rule.get("action") or {}
            target_agent = act.get("target_agent") or event.agent
            action = act.get("type") or event.event
            confidence = float(rule.get("confidence", 0.8)) if rule.get("confidence") else 0.8

        return rule

    return None


def guardian_precheck(
    decision: "Decision",
    agent_profile: Dict[str, Any],
    rule: Optional[Dict[str, Any]] = None,
) -> Tuple[bool, Optional[str]]:
    """
    Einfache Guardian-Logik V2 (Precheck):
    - Prüft, ob der Agent aktiv ist.
    - Prüft optional min. Autonomie-Level aus der Regel.
    Gibt (allowed, guardian_flag) zurück.
    """
    status = (agent_profile or {}).get("status", "unknown")
    if status != "active":
        return False, "agent_inactive"

    # Autonomie-Anforderungen aus Regel
    required_autonomy = 0.0
    if rule:
        then_cfg = rule.get("then", {}) or {}
        required_autonomy = float(then_cfg.get("min_autonomy", 0.0))

    agent_autonomy = float((agent_profile or {}).get("autonomy", 0.0))
    if agent_autonomy < required_autonomy:
        return False, "autonomy_too_low"

    return True, None


def execute_agent_action(
    agent: str,
    action: str,
    event: "Event",
    agent_profile: Dict[str, Any],
) -> Tuple[bool, str]:
    """
    MVP-Ausführung.
    Aktuell: Simulation – hier können später echte Agent-Adapter eingebaut werden.
    Rückgabe: (success, result_summary)
    """
    # TODO: Echte Adapter einhängen (deploy_agent.py, monitoring_agent.py, audit_agent.py, Content-Agent, ...)
    # Für jetzt: Wir loggen nur, dass eine Aktion "geplant" wurde.
    summary = (
        f"Simulated execution: agent='{agent}', action='{action}', "
        f"event_id='{event.id}', role='{agent_profile.get('role', 'n/a')}'."
    )
    success = True
    return success, summary


def guardian_postcheck(
    decision: "Decision",
    agent_profile: Dict[str, Any],
    health: "HealthState",
    success: bool,
) -> Optional[str]:
    """
    Vereinfachter Guardian-Postcheck:
    - Aktualisiert HealthState
    - Setzt bei Fehlern ein Guardian-Flag, nutzt optional failure_thresholds aus autonomy.json.
    """
    health.register_result(success=success)

    if success:
        health.last_autonomous_action = f"{decision.agent}:{decision.action}"
        return None

    # Fehlerfall → Guardian-Flag
    failure_thresholds = (agent_profile or {}).get("failure_thresholds", {}) or {}
    guardian_flag = "error_detected"

    # Beispiel: wenn 'trigger_guardian_policy_check' konfiguriert ist
    if failure_thresholds.get("trigger_guardian_policy_check"):
        guardian_flag = "guardian_policy_check"

    return guardian_flag


# ---------------------------------------------------------------------------
# Haupt-Orchestrierungsfunktion
# ---------------------------------------------------------------------------

def orchestrate() -> Optional["Decision"]:
    """
    Führt einen Orchestrierungszyklus aus:
    - Holt letztes Event
    - Wendet GEORGE-Regeln an
    - Prüft Autonomie/Guardian
    - Führt Agentenaktion (simuliert) aus
    - Persistiert Decision + Health + Snapshots
    """
    # 1) Not-Aus prüfen
    if emergency_lock_active():
        print("[GEORGE V2] Emergency Lock ist aktiv – Orchestrierung gestoppt.", file=sys.stderr)
        return None

    # 2) Letztes Event laden
    event = load_latest_event()
    if not event:
        # Kein Event ⇒ keine Entscheidung
        return None

    # 3) Regeln & Autonomie-Config laden
    rules = load_rules()
    autonomy_cfg = load_autonomy_config()
    agent_profile = get_agent_profile(event.agent)

    # 4) Passende Regel suchen
    rule = match_rule_for_event(event, rules)
    if rule:
        then_cfg = rule.get("then", {}) or {}
        target_agent = then_cfg.get("agent") or event.agent
        action = then_cfg.get("action") or event.event
        confidence = float(then_cfg.get("confidence", 0.8))
    else:
        # Fallback: Agent & Aktion direkt aus dem Event ableiten
        target_agent = event.agent
        action = event.event
        confidence = 0.5

    target_profile = get_agent_profile(target_agent)

    # 5) Decision-Objekt erzeugen (zunächst pending)
    decision = Decision(
        id=str(uuid.uuid4()),
        timestamp=now_iso(),
        source_event_id=event.id,
        agent=target_agent,
        action=action,
        intent=event.intent,
        confidence=confidence,
        status="pending",
        error_message=None,
        guardian_flag=None,
        follow_up=None,
        result_summary=None,
    )

    # 6) Guardian-Precheck
    allowed, guardian_flag = guardian_precheck(decision, target_profile, rule)
    if not allowed:
        decision.status = "blocked"
        decision.guardian_flag = guardian_flag or "blocked_by_guardian"
        save_decision(decision)
        print(f"[GEORGE V2] Decision {decision.id} BLOCKED durch Guardian: {decision.guardian_flag}")
        return decision

    # 7) Aktion ausführen (aktuell simuliert)
    success, result_summary = execute_agent_action(
        agent=target_agent,
        action=action,
        event=event,
        agent_profile=target_profile or {},
    )

    decision.result_summary = result_summary
    decision.status = "success" if success else "error"
    if not success:
        decision.error_message = "Agent execution failed (simulated)."

    # 8) HealthState laden, Postcheck ausführen, speichern
    health = load_health()
    guardian_flag_post = guardian_postcheck(decision, target_profile or {}, health, success)
    if guardian_flag_post:
        decision.guardian_flag = guardian_flag_post

    save_health(health)

    # 9) Decision persistieren (History + latest + Snapshot)
    save_decision(decision)

    print(
        f"[GEORGE V2] Decision {decision.id}: "
        f"agent='{decision.agent}', action='{decision.action}', status='{decision.status}'"
    )
    return decision


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------

def main() -> None:
    """
    Einmalige Orchestrierungsrunde für CLI / GitHub Actions.
    """
    decision = orchestrate()
    if not decision:
        print("[GEORGE V2] Keine Decision getroffen (kein Event oder Emergency Lock aktiv).")
    else:
        print(
            f"[GEORGE V2] Fertig – Decision {decision.id} -> {decision.status}, "
            f"guardian_flag={decision.guardian_flag!r}"
        )


if __name__ == "__main__":
    main()
