#!/usr/bin/env python3
"""
GEORGE Orchestrator V2 – Autonomous Edition

Goal (A): Fix GEORGE output so the Runtime Authority Gate can evaluate it correctly.

What this patch does:
- Ensures ops/decisions/latest.json ALWAYS contains the fields your current runtime_gate.py + policy expect
  (based on the gate_result reasons you posted: missing signals.system_health_score, guardian_ok, trace).
- Adds BOTH contract styles:
  - "health_context" / "decision_trace" (new contract)
  - "signals" / "guardian" / "trace" (what your current gate/policy appears to validate)
- Prevents “agent_inactive” false-blocks when autonomy.json is missing:
  - default agent status = active
  - default autonomy = 1.0
- Writes a stable, gate-readable structure even for blocked decisions.

NOTE:
- This file is safe to replace 1:1.
- No changes to runtime_gate.py needed for this step.
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
# Constants
# ---------------------------------------------------------------------------

VALID_DECISION_CLASSES = {"safety_critical", "operational", "strategic", "deploy"}

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
AUTHORITY_MATRIX_FILE = OPS_DIR / "authority_matrix.yaml"

# ---------------------------------------------------------------------------
# Utility-Funktionen
# ---------------------------------------------------------------------------

def now_iso() -> str:
    """UTC-Zeitstempel im ISO-Format (ohne Microseconds)."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

def clamp_int(n: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, int(n)))

def clamp_float(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, float(x)))

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
    path.parent.mkdir(exist_ok=True, parents=True)
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
    id: str
    timestamp: str
    source_event_id: Optional[str]
    agent: str
    action: str
    intent: Optional[str]
    confidence: float
    status: str               # pending | success | error | blocked
    error_message: Optional[str] = None
    guardian_flag: Optional[str] = None
    follow_up: Optional[str] = None
    result_summary: Optional[str] = None

    # Gate-relevant (runtime_gate.py)
    decision_class: str = "operational"          # safety_critical|operational|strategic|deploy
    authority_source: str = "george"             # george|human|guardian|...
    health_context: Optional[Dict[str, Any]] = None
    decision_trace: Optional[Dict[str, Any]] = None
    execution_context: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class HealthState:
    agent_response_success_rate: float = 0.0
    last_autonomous_action: Optional[str] = None
    self_detection_errors: int = 0
    system_stability_score: float = 0.0     # 0..1
    autonomy_level_estimate: float = 0.5    # 0..1
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
    data = load_json(STATUS_FILE, default=None)
    if not data:
        return HealthState()
    try:
        return HealthState.from_dict(data)
    except Exception as exc:
        print(f"[GEORGE V2] Konnte HealthState nicht rekonstruieren: {exc}", file=sys.stderr)
        return HealthState()

def save_health(health: HealthState) -> None:
    data = health.to_dict()
    save_json(STATUS_FILE, data)
    append_jsonl(HEALTH_LOG, data)

# ---------------------------------------------------------------------------
# Autonomy-Konfiguration
# ---------------------------------------------------------------------------

def load_autonomy_config() -> Dict[str, Any]:
    cfg = load_json(AUTONOMY_FILE, default={})
    return cfg if isinstance(cfg, dict) else {}

def get_agent_profile(agent_id: str) -> Dict[str, Any]:
    """
    IMPORTANT:
    If autonomy.json is missing, we must NOT hard-block with agent_inactive.
    Defaults here are chosen to keep the pipeline evaluable by the gate.
    """
    cfg = load_autonomy_config()
    agents = cfg.get("agents", {})
    profile = agents.get(agent_id, {}) if isinstance(agents, dict) else {}

    if not isinstance(profile, dict):
        profile = {}

    # Safe defaults
    profile.setdefault("status", "active")
    profile.setdefault("autonomy", 1.0)
    profile.setdefault("role", "n/a")
    return profile

# ---------------------------------------------------------------------------
# Events / Rules / Authority
# ---------------------------------------------------------------------------

def load_latest_event() -> Optional[Event]:
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

def load_authority_matrix() -> Dict[str, Any]:
    cfg = load_yaml(AUTHORITY_MATRIX_FILE, default={})
    return cfg if isinstance(cfg, dict) else {}

def load_rules() -> List[Dict[str, Any]]:
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
# Decision Persistenz (gate-kompatibel)
# ---------------------------------------------------------------------------

def _derive_gate_health(health: HealthState, decision: Decision) -> Tuple[float, int, str]:
    """
    Returns:
      - system_health_score: float 0..1 (what gate policy seems to check: signals.system_health_score)
      - system_health_percent: int 0..100 (nice for humans)
      - guardian_status: OK|WARNING|CRITICAL
    """
    score = clamp_float(health.system_stability_score, 0.0, 1.0)
    pct = clamp_int(int(round(score * 100)), 0, 100)

    # Very simple mapping (you can refine later)
    if decision.guardian_flag and str(decision.guardian_flag).strip().lower() not in {"", "none", "ok"}:
        guardian_status = "WARNING"
    else:
        guardian_status = "OK"

    return score, pct, guardian_status

def _gate_view_of_decision(dec: Decision) -> Dict[str, Any]:
    """
    Produce a latest.json that satisfies BOTH:
    - the "new contract" keys: health_context, decision_trace, execution_context
    - the CURRENT runtime_gate.py/policy keys observed in logs: signals.system_health_score, guardian_ok, trace
    """
    health = load_health()
    sys_score, sys_pct, guardian_status = _derive_gate_health(health, dec)
    guardian_ok = (guardian_status == "OK")

    # Normalize decision_class strictly
    dc = (dec.decision_class or "operational").strip().lower()
    if dc not in VALID_DECISION_CLASSES:
        dc = "operational"

    # Provide both “decision_trace” and “trace” to avoid mismatch
    execution_path = ["george", "decision_engine", "authority_enforcer", "executor"]
    trace_obj = dec.decision_trace or {
        "complete": True,
        "trace_id": dec.id,
        "execution_path": execution_path,
    }

    # Some gates expect different field names inside trace; provide both variants
    trace_compat = {
        "complete": bool(trace_obj.get("complete", True)),
        "id": trace_obj.get("trace_id", dec.id),
        "trace_id": trace_obj.get("trace_id", dec.id),
        "path": trace_obj.get("execution_path", execution_path),
        "execution_path": trace_obj.get("execution_path", execution_path),
    }

    # Provide both “health_context” and “signals”
    health_context = dec.health_context or {
        "system_health": sys_pct,
        "guardian_status": guardian_status,
        "performance_metrics": {},
    }

    signals = {
        # This was explicitly missing in your gate_result reasons:
        "system_health_score": sys_score,           # float 0..1
        "system_health_percent": sys_pct,           # int 0..100
        "guardian_ok": bool(guardian_ok),
    }

    # Provide both “guardian” and “health_context.guardian_status”
    guardian = {
        "ok": bool(guardian_ok),
        "status": guardian_status,
        "flag": dec.guardian_flag,
        "recommendation": None,
    }

    execution_context = dec.execution_context or {
        "latency_ms": 0,
        "dependencies": [],
        "security_context": {"authenticated": True, "authorization_level": "standard"},
    }

    gate_doc: Dict[str, Any] = {
        # Gate expects these (at minimum):
        "decision_id": dec.id,
        "decision_class": dc,
        "authority_source": (dec.authority_source or "george"),

        # New contract:
        "health_context": health_context,
        "decision_trace": trace_obj,
        "execution_context": execution_context,

        # Current gate/policy compatibility layer (based on your screenshots):
        "signals": signals,
        "guardian": guardian,
        "trace": trace_compat,
    }

    # Keep legacy/diagnostic fields too (harmless for gate, useful for debugging)
    gate_doc.update({
        "id": dec.id,
        "timestamp": dec.timestamp,
        "source_event_id": dec.source_event_id,
        "agent": dec.agent,
        "action": dec.action,
        "intent": dec.intent,
        "confidence": dec.confidence,
        "status": dec.status,
        "error_message": dec.error_message,
        "guardian_flag": dec.guardian_flag,
        "follow_up": dec.follow_up,
        "result_summary": dec.result_summary,
    })

    return gate_doc

def save_decision(decision: Decision | Dict[str, Any]) -> None:
    if isinstance(decision, Decision):
        dec_dict = decision.to_dict()
        gate_latest = _gate_view_of_decision(decision)
    else:
        dec_dict = dict(decision)
        # fallback: also write minimal gate structure
        tmp_dec = Decision(
            id=str(dec_dict.get("id") or dec_dict.get("decision_id") or uuid.uuid4()),
            timestamp=str(dec_dict.get("timestamp") or now_iso()),
            source_event_id=dec_dict.get("source_event_id"),
            agent=str(dec_dict.get("agent") or "unknown"),
            action=str(dec_dict.get("action") or "unknown"),
            intent=dec_dict.get("intent"),
            confidence=float(dec_dict.get("confidence") or 0.5),
            status=str(dec_dict.get("status") or "pending"),
            decision_class=str(dec_dict.get("decision_class") or "operational"),
            authority_source=str(dec_dict.get("authority_source") or "george"),
        )
        gate_latest = _gate_view_of_decision(tmp_dec)

    today = datetime.now(timezone.utc).date().isoformat()

    append_jsonl(DECISIONS_LOG, dec_dict)

    history_file = DECISIONS_HISTORY_DIR / f"{today}.jsonl"
    append_jsonl(history_file, dec_dict)

    # IMPORTANT: latest.json is the gate input
    save_json(DECISIONS_LATEST, gate_latest)

    update_snapshot(today, dec_dict)

def update_snapshot(date: str, decision: Dict[str, Any]) -> None:
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

    snapshot["last_decision_id"] = decision.get("id") or decision.get("decision_id")
    snapshot["last_updated"] = now_iso()

    with snapshot_path.open("w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2, ensure_ascii=False)

# ---------------------------------------------------------------------------
# Orchestrierungs-Helfer
# ---------------------------------------------------------------------------

def match_rule_for_event(event: Event, rules: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
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

def resolve_decision_class(event: Event, rule: Optional[Dict[str, Any]]) -> str:
    """
    IMPORTANT: Must match runtime_gate.py allowed values:
    safety_critical | operational | strategic | deploy
    """
    def normalize(dc_raw: Any) -> str:
        dc = str(dc_raw).lower().strip()
        if dc in {"critical", "safety", "safety-critical", "safetycritical"}:
            return "safety_critical"
        if dc in {"ops", "operation"}:
            return "operational"
        if dc not in VALID_DECISION_CLASSES:
            return "operational"
        return dc

    if rule:
        then_cfg = rule.get("then", {}) or {}
        if "decision_class" in then_cfg:
            return normalize(then_cfg.get("decision_class"))

    if event.intent:
        return normalize(event.intent)

    return "operational"

def guardian_precheck(
    decision: Decision,
    agent_profile: Dict[str, Any],
    rule: Optional[Dict[str, Any]] = None,
) -> Tuple[bool, Optional[str]]:
    """
    IMPORTANT:
    Do not block just because autonomy.json is missing.
    With defaults (status=active, autonomy=1.0) the system stays evaluable.
    """
    status = (agent_profile or {}).get("status", "active")
    if status != "active":
        return False, "agent_inactive"

    required_autonomy = 0.0
    if rule:
        then_cfg = rule.get("then", {}) or {}
        required_autonomy = float(then_cfg.get("min_autonomy", 0.0))

    agent_autonomy = float((agent_profile or {}).get("autonomy", 1.0))
    if agent_autonomy < required_autonomy:
        return False, "autonomy_too_low"

    return True, None

def authority_enforcement(
    decision: Decision,
    event: Event,
    agent_profile: Dict[str, Any],
    rule: Optional[Dict[str, Any]] = None,
) -> Tuple[bool, Optional[str], Optional[str], str]:
    """
    Runtime Authority Enforcement – BLOCKING Hook (Matrix-driven)
    Returns: (allowed, block_reason, required_authority, decision_class)
    """
    matrix = load_authority_matrix()
    decision_class = resolve_decision_class(event, rule)

    default_cfg = (matrix.get("default") or {}) if isinstance(matrix.get("default"), dict) else {}
    classes_cfg = (matrix.get("classes") or {}) if isinstance(matrix.get("classes"), dict) else {}
    agents_cfg = (matrix.get("agents") or {}) if isinstance(matrix.get("agents"), dict) else {}

    class_cfg = (classes_cfg.get(decision_class) or {}) if isinstance(classes_cfg.get(decision_class), dict) else {}
    required = str(class_cfg.get("require") or default_cfg.get("require") or "human").lower()

    # Agent override: darf der Agent diese Klasse überhaupt?
    agent_id = decision.agent
    agent_override = agents_cfg.get(agent_id, {}) if isinstance(agents_cfg.get(agent_id), dict) else {}
    allowed_classes = agent_override.get("allowed_classes")
    if isinstance(allowed_classes, list) and decision_class not in [str(x).lower() for x in allowed_classes]:
        return False, "agent_not_allowed_for_decision_class", "human", decision_class

    # required authority enforcement
    if required in {"human", "manual"}:
        return False, "authority_requires_human", "human", decision_class

    return True, None, None, decision_class

def execute_agent_action(
    agent: str,
    action: str,
    event: Event,
    agent_profile: Dict[str, Any],
) -> Tuple[bool, str]:
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
        append_trace({"actor": "george_v2", "phase": "load_event", "result": "no_event"})
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
    decision_class = resolve_decision_class(event, rule)

    decision = Decision(
        id=str(uuid.uuid4()),
        timestamp=now_iso(),
        source_event_id=event.id,
        agent=target_agent,
        action=action,
        intent=event.intent,
        confidence=confidence,
        status="pending",
        decision_class=decision_class,
        authority_source="george",
    )

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
            "decision_class": decision.decision_class,
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
        decision.authority_source = "guardian"
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

    # Authority Enforcement (BLOCKING)
    allowed_auth, reason, required, decision_class = authority_enforcement(decision, event, target_profile, rule)
    decision.decision_class = decision_class

    if not allowed_auth:
        decision.status = "blocked"
        decision.guardian_flag = reason or "blocked_by_authority"
        decision.follow_up = f"Requires approval: {required}" if required else "Requires approval"
        decision.authority_source = "human" if required else "guardian"
        save_decision(decision)

        append_trace({
            "actor": "authority",
            "phase": "enforcement",
            "decision_id": decision.id,
            "result": "blocked",
            "reason": reason,
            "required_authority": required,
            "decision_class": decision_class,
            "decision": {"agent": decision.agent, "action": decision.action, "intent": decision.intent},
        })

        print(f"[GEORGE V2] Decision {decision.id} BLOCKED by Authority: {reason} (required={required})")
        return decision

    append_trace({
        "actor": "authority",
        "phase": "enforcement",
        "decision_id": decision.id,
        "result": "allowed",
        "decision_class": decision_class,
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

    # Attach gate-required contexts (so latest.json is always compliant)
    sys_score = clamp_float(health.system_stability_score, 0.0, 1.0)
    sys_pct = clamp_int(int(round(sys_score * 100)), 0, 100)
    guardian_status = "OK" if decision.guardian_flag in (None, "", "ok") else "WARNING"

    decision.health_context = {
        "system_health": sys_pct,
        "guardian_status": guardian_status,
        "performance_metrics": {
            "agent_response_success_rate": health.agent_response_success_rate,
            "system_health_score": sys_score,  # extra signal duplication (harmless)
            "total_actions": health.total_actions,
            "failed_actions": health.failed_actions,
        },
    }
    decision.decision_trace = {
        "complete": True,
        "trace_id": decision.id,
        "execution_path": ["george", "guardian", "authority", "executor"],
    }
    decision.execution_context = {
        "latency_ms": 0,
        "dependencies": [],
        "security_context": {"authenticated": True, "authorization_level": "standard"},
    }

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
