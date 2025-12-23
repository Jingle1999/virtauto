#!/usr/bin/env python3
"""
GEORGE Orchestrator V2 – Autonomous Edition

Ziele:
- Aus eingehenden Events echte Entscheidungen machen (Decisions)
- Guardian-Checks vor und nach der Ausführung
- Agenten-Aktionen ausführen (oder simulieren, falls kein Adapter vorhanden)
- Persistenzschicht für Decisions + Health-Metriken + Events
- Decision Trace (Step 3): lückenlose, maschinenlesbare Nachverfolgbarkeit
"""

from __future__ import annotations

import json
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

# Legacy status.json bleibt bestehen (wird von dir schon als deprecated behandelt).
# Health-Persistenz für V2:
STATUS_FILE = OPS_DIR / "status.json"

REPORTS_DIR = OPS_DIR / "reports"
REPORTS_DIR.mkdir(exist_ok=True, parents=True)

DECISIONS_LOG = REPORTS_DIR / "george_decisions.jsonl"
DECISION_TRACE_LOG = REPORTS_DIR / "decision_trace.jsonl"
HEALTH_LOG = REPORTS_DIR / "health_log.jsonl"

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


def append_jsonl(path: Path, record: Dict[str, Any]) -> None:
    path.parent.mkdir(exist_ok=True, parents=True)
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


def append_trace(record: Dict[str, Any]) -> None:
    """
    Decision Trace (Step 3):
    - JSONL
    - Keine Interpretation, nur Fakten / Inputs / Outputs
    """
    record = dict(record)
    record.setdefault("ts", now_iso())
    record.setdefault("trace_version", "v1")
    append_jsonl(DECISION_TRACE_LOG, record)


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

        # Simple Heuristik für Stabilität & Autonomie
        self.system_stability_score = max(
            0.0,
            min(1.0, self.agent_response_success_rate * (1.0 - 0.1 * self.self_detection_errors)),
        )
        self.autonomy_level_estimate = max(
            0.0,
            min(1.0, 0.4 + 0.6 * self.system_stability_score),
        )


# ---------------------------------------------------------------------------
# Health Persistenz
# ---------------------------------------------------------------------------

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
    append_jsonl(HEALTH_LOG, data)


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
    """Liefert das Agent-Profil aus autonomy.json."""
    cfg = load_autonomy_config()
    agents = cfg.get("agents", {})
    profile = agents.get(agent_id, {})
    if not isinstance(profile, dict):
        return {}
    return profile


# ---------------------------------------------------------------------------
# Events / Rules
# ---------------------------------------------------------------------------

def load_latest_event() -> Optional[Event]:
    """Liest das letzte Event aus events.jsonl (eine JSON-Zeile pro Event)."""
    if not EVENTS_FILE.exists():
        print("[GEORGE V2] Keine events.jsonl gefunden.")
        return None

    last_line = None
    with EVENTS_FILE.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                last_line = line

    if not last_line:
        print("[GEORGE V2] events.jsonl ist leer.")
        return None

    try:
        return Event.from_dict(json.loads(last_line))
    except Exception as exc:
        print(f"[GEORGE V2] Fehler beim Laden letztes JSONL-Event: {exc}", file=sys.stderr)
        return None


def append_events(new_events: List[Event]) -> None:
    """Hängt Events an events.jsonl an."""
    with EVENTS_FILE.open("a", encoding="utf-8") as f:
        for ev in new_events:
            f.write(json.dumps(ev.to_dict(), ensure_ascii=False) + "\n")


def load_rules() -> List[Dict[str, Any]]:
    """Lädt die GEORGE-Rules aus george_rules.yaml."""
    data = load_yaml(RULES_FILE, default={})
    if isinstance(data, dict):
        rules = data.get("rules", [])
    else:
        rules = data or []

    if not isinstance(rules, list):
        print("[GEORGE V2] Ungültiges Rules-Format in george_rules.yaml", file=sys.stderr)
        return []

    return rules


# ---------------------------------------------------------------------------
# Decision Persistenz
# ---------------------------------------------------------------------------

def save_decision(decision: Decision | Dict[str, Any]) -> None:
    """
    Persistiert eine Decision in:
    - reports/george_decisions.jsonl (zentral, append)
    - decisions/history/YYYY-MM-DD.jsonl (append)
    - decisions/latest.json (overwrite)
    - decisions/snapshots/YYYY-MM-DD.json (aggregate)
    """
    if isinstance(decision, Decision):
        dec_dict = decision.to_dict()
    else:
        dec_dict = dict(decision)

    today = datetime.now(timezone.utc).date().isoformat()

    # 0) Zentraler Log
    append_jsonl(DECISIONS_LOG, dec_dict)

    # 1) History-Log (append)
    history_file = DECISIONS_HISTORY_DIR / f"{today}.jsonl"
    append_jsonl(history_file, dec_dict)

    # 2) latest.json
    with DECISIONS_LATEST.open("w", encoding="utf-8") as f:
        json.dump(dec_dict, f, indent=2, ensure_ascii=False)

    # 3) Snapshot aktualisieren
    update_snapshot(today, dec_dict)


def update_snapshot(date: str, decision: Dict[str, Any]) -> None:
    """
    Tages-Snapshot:
    - total_decisions
    - successful / error / blocked
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

    snapshot.setdefault("date", date)
    snapshot.setdefault("total_decisions", 0)
    snapshot.setdefault("successful", 0)
    snapshot.setdefault("error", 0)
    snapshot.setdefault("blocked", 0)
    snapshot.setdefault("by_agent", {})

    agent = decision.get("agent", "unknown")
    status = decision.get("status", "unknown")

    snapshot["total_decisions"] += 1
    if status == "success":
        snapshot["successful"] += 1
    elif status == "error":
        snapshot["error"] += 1
    elif status == "blocked":
        snapshot["blocked"] += 1

    if agent not in snapshot["by_agent"]:
        snapshot["by_agent"][agent] = {"total": 0, "success": 0, "error": 0, "blocked": 0}

    snapshot["by_agent"][agent]["total"] += 1
    if status == "success":
        snapshot["by_agent"][agent]["success"] += 1
    elif status == "error":
        snapshot["by_agent"][agent]["error"] += 1
    elif status == "blocked":
        snapshot["by_agent"][agent]["blocked"] += 1

    snapshot["last_decision_id"] = decision.get("id")
    snapshot["last_updated"] = now_iso()

    with snapshot_path.open("w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Orchestrierungs-Helfer
# ---------------------------------------------------------------------------

def match_rule_for_event(event: Event, rules: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Findet die erste passende Regel aus george_rules.yaml für das Event.
    Tolerant: wenn Felder in 'when' fehlen, werden sie ignoriert.
    Unterstützte Keys (optional): agent, event, intent, source_event_id
    """
    if not rules:
        return None

    for rule in rules:
        when = rule.get("when", {}) or {}

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

        return rule

    return None


def guardian_precheck(
    decision: Decision,
    agent_profile: Dict[str, Any],
    rule: Optional[Dict[str, Any]] = None,
) -> Tuple[bool, Optional[str]]:
    """
    Guardian Precheck (MVP):
    - Agent muss active sein
    - optional: min_autonomy aus Regel (then.min_autonomy)
    """
    status = (agent_profile or {}).get("status", "unknown")
    if status != "active":
        return False, "agent_inactive"

    required_autonomy = 0.0
    if rule:
        then_cfg = rule.get("then", {}) or {}
        required_autonomy = float(then_cfg.get("min_autonomy", 0.0))

    agent_autonomy = float((agent_profile or {}).get("autonomy", 0.0))
    if agent_autonomy < required_autonomy:
        return False, "autonomy_too_low"

    return True, None


def authority_enforcement(
    decision: Decision,
    event: Event,
    agent_profile: Dict[str, Any],
    rule: Optional[Dict[str, Any]] = None,
) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Runtime Authority Enforcement (MVP) – BLOCKING Hook.
    Returns: (allowed, block_reason, required_authority)

    Aktueller MVP-Policy-Entscheid:
    - decision_class "deploy" oder "safety" => block (requires human)
    - sonst => allow
    """
    # 1) Decision-Class bestimmen (erst rule, dann event.intent, fallback)
    decision_class = None
    if rule:
        then_cfg = rule.get("then", {}) or {}
        decision_class = then_cfg.get("decision_class")

    decision_class = (decision_class or event.intent or "operational").lower()

    # 2) Policy (MVP)
    if decision_class in {"deploy", "safety"}:
        return False, "authority_requires_human", "human"

    return True, None, None


def execute_agent_action(
    agent: str,
    action: str,
    event: Event,
    agent_profile: Dict[str, Any],
) -> Tuple[bool, str]:
    """
    MVP-Ausführung (aktuell Simulation).
    Später: echte Adapter hier einhängen.
    """
    summary = (
        f"Simulated execution: agent='{agent}', action='{action}', "
        f"event_id='{event.id}', role='{agent_profile.get('role', 'n/a')}'."
    )
    return True, summary


def guardian_postcheck(
    decision: Decision,
    agent_profile: Dict[str, Any],
    health: HealthState,
    success: bool,
) -> Optional[str]:
    """
    Guardian Postcheck (MVP):
    - aktualisiert HealthState
    - setzt bei Fehlern guardian_flag (optional thresholds aus autonomy.json)
    """
    health.register_result(success=success)

    if success:
        health.last_autonomous_action = f"{decision.agent}:{decision.action}"
        return None

    failure_thresholds = (agent_profile or {}).get("failure_thresholds", {}) or {}
    guardian_flag = "error_detected"

    if failure_thresholds.get("trigger_guardian_policy_check"):
        guardian_flag = "guardian_policy_check"

    return guardian_flag


# ---------------------------------------------------------------------------
# Haupt-Orchestrierungsfunktion
# ---------------------------------------------------------------------------

def orchestrate() -> Optional[Decision]:
    """
    Orchestrierungszyklus:
    - Not-Aus prüfen
    - letztes Event lesen
    - Regel matchen
    - Guardian Precheck
    - Authority Enforcement (blocking)
    - Aktion ausführen (simuliert)
    - Guardian Postcheck
    - Persistenz + Decision Trace
    """
    if emergency_lock_active():
        append_trace({
            "actor": "george_v2",
            "phase": "emergency_lock",
            "result": "stopped",
            "reason": "emergency_lock_active",
        })
        print("[GEORGE V2] Emergency Lock ist aktiv – Orchestrierung gestoppt.", file=sys.stderr)
        return None

    event = load_latest_event()
    if not event:
        append_trace({
            "actor": "george_v2",
            "phase": "load_event",
            "result": "no_event",
        })
        return None

    rules = load_rules()
    rule = match_rule_for_event(event, rules)

    if rule:
        then_cfg = rule.get("then", {}) or {}
        target_agent = then_cfg.get("agent") or event.agent
        action = then_cfg.get("action") or event.event
        confidence = float(then_cfg.get("confidence", 0.8))
        matched_rule_id = rule.get("id")
    else:
        target_agent = event.agent
        action = event.event
        confidence = 0.5
        matched_rule_id = None

    target_profile = get_agent_profile(target_agent)

    # Decision anlegen
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

    # TRACE: Routing
    append_trace({
        "actor": "george_v2",
        "phase": "route",
        "event": {
            "id": event.id,
            "agent": event.agent,
            "event": event.event,
            "intent": event.intent,
            "source_event_id": event.source_event_id,
        },
        "matched_rule_id": matched_rule_id,
        "decision": {
            "id": decision.id,
            "target_agent": target_agent,
            "action": action,
            "confidence": confidence,
            "status": decision.status,
        },
        "result": "routed",
    })

    # Guardian Precheck
    allowed, guardian_flag = guardian_precheck(decision, target_profile, rule)
    if not allowed:
        decision.status = "blocked"
        decision.guardian_flag = guardian_flag or "blocked_by_guardian"
        save_decision(decision)

        append_trace({
            "actor": "guardian",
            "phase": "precheck",
            "decision_id": decision.id,
            "result": "blocked",
            "guardian_flag": decision.guardian_flag,
            "target_agent": target_agent,
            "action": action,
        })

        print(f"[GEORGE V2] Decision {decision.id} BLOCKED durch Guardian: {decision.guardian_flag}")
        return decision

    append_trace({
        "actor": "guardian",
        "phase": "precheck",
        "decision_id": decision.id,
        "result": "allowed",
        "target_agent": target_agent,
        "action": action,
    })

    # --- Authority Enforcement (BLOCKING) ---
    allowed_auth, reason, required = authority_enforcement(decision, event, target_profile, rule)
    if not allowed_auth:
        decision.status = "blocked"
        decision.guardian_flag = reason or "blocked_by_authority"
        decision.follow_up = f"Requires approval: {required}" if required else "Requires approval"
        save_decision(decision)

        append_trace({
            "actor": "authority",
            "phase": "enforcement",
            "decision_id": decision.id,
            "result": "blocked",
            "reason": reason,
            "required_authority": required,
            "decision": {"agent": decision.agent, "action": decision.action, "intent": decision.intent},
        })

        print(f"[GEORGE V2] Decision {decision.id} BLOCKED by Authority: {reason} (required={required})")
        return decision

    append_trace({
        "actor": "authority",
        "phase": "enforcement",
        "decision_id": decision.id,
        "result": "allowed",
        "decision": {"agent": decision.agent, "action": decision.action, "intent": decision.intent},
    })

    # Aktion ausführen (simuliert)
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

    append_trace({
        "actor": "executor",
        "phase": "execute",
        "decision_id": decision.id,
        "target_agent": target_agent,
        "action": action,
        "result": "success" if success else "error",
        "result_summary": (result_summary or "")[:500],
    })

    # Health + Postcheck
    health = load_health()
    guardian_flag_post = guardian_postcheck(decision, target_profile or {}, health, success)
    if guardian_flag_post:
        decision.guardian_flag = guardian_flag_post

    save_health(health)

    append_trace({
        "actor": "guardian",
        "phase": "postcheck",
        "decision_id": decision.id,
        "result": "ok" if success else "flagged",
        "guardian_flag": decision.guardian_flag,
        "health": {
            "agent_response_success_rate": health.agent_response_success_rate,
            "system_stability_score": health.system_stability_score,
            "autonomy_level_estimate": health.autonomy_level_estimate,
            "total_actions": health.total_actions,
            "failed_actions": health.failed_actions,
        },
    })

    # Decision persistieren
    save_decision(decision)

    append_trace({
        "actor": "george_v2",
        "phase": "finalize",
        "decision_id": decision.id,
        "result": decision.status,
        "guardian_flag": decision.guardian_flag,
    })

    print(
        f"[GEORGE V2] Decision {decision.id}: "
        f"agent='{decision.agent}', action='{decision.action}', status='{decision.status}'"
    )
    return decision


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------

def main() -> None:
    """Einmalige Orchestrierungsrunde für CLI / GitHub Actions."""
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
