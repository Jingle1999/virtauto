#!/usr/bin/env python3
"""
GEORGE Orchestrator V2 – Autonomous Edition (Gate-Contract hardened)

Key updates (Runtime Gate Contract):
- Writes a runtime_gate-compatible ops/decisions/latest.json structure
- Writes ops/decisions/canonical_latest.json as canonical stable shape
- Ensures BOTH keys exist: `decision_trace` AND `trace` (alias)
- Ensures REQUIRED runtime_gate inputs exist:
    - decision_class
    - signals.system_health_score (0..1 float)
    - signals.guardian_ok (bool)
    - signals.status_endpoint_ok (bool)
    - signals.decision_trace_present (bool)
- authority_enforcement() returns 4 values (allowed, reason, required, decision_class)
- Always includes helpful context blocks: health_context, execution_context, guardian
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
# Paths (repo-relative)
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

# Gate reads this:
DECISIONS_LATEST = DECISIONS_DIR / "latest.json"

# Canonical (stable shape for humans/tools):
CANONICAL_LATEST = DECISIONS_DIR / "canonical_latest.json"

AUTONOMY_FILE = OPS_DIR / "autonomy.json"
AUTHORITY_MATRIX_FILE = OPS_DIR / "authority_matrix.yaml"


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def now_iso() -> str:
    """UTC timestamp ISO."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        print(f"[WARN] JSON parse failed: {path} – using default.", file=sys.stderr)
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
    - Facts only (inputs/outputs)
    """
    record = dict(record)
    record.setdefault("ts", now_iso())
    record.setdefault("trace_version", "v1")
    append_jsonl(DECISION_TRACE_LOG, record)


def _safe_load_status() -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Interprets 'status endpoint ok' as: status.json exists and is valid JSON.
    (No HTTP endpoint in this repo context.)
    """
    if not STATUS_FILE.exists():
        return False, None
    try:
        data = load_json(STATUS_FILE, default=None)
        if not isinstance(data, dict):
            return False, None
        return True, data
    except Exception:
        return False, None


# ---------------------------------------------------------------------------
# Models
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
    status: str  # pending | success | error | blocked
    error_message: Optional[str] = None
    guardian_flag: Optional[str] = None
    follow_up: Optional[str] = None
    result_summary: Optional[str] = None

    # Gate-relevant
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
    system_stability_score: float = 0.0   # IMPORTANT: 0..1 float (Gate expects 0..1 for system_health_score)
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

        self.system_stability_score = max(
            0.0,
            min(1.0, self.agent_response_success_rate * (1.0 - 0.1 * self.self_detection_errors)),
        )
        self.autonomy_level_estimate = max(
            0.0,
            min(1.0, 0.4 + 0.6 * self.system_stability_score),
        )


# ---------------------------------------------------------------------------
# Health persistence
# ---------------------------------------------------------------------------

def load_health() -> HealthState:
    data = load_json(STATUS_FILE, default=None)
    if not data:
        return HealthState()
    try:
        return HealthState.from_dict(data)
    except Exception as exc:
        print(f"[GEORGE V2] Cannot reconstruct HealthState: {exc}", file=sys.stderr)
        return HealthState()


def save_health(health: HealthState) -> None:
    data = health.to_dict()
    save_json(STATUS_FILE, data)
    append_jsonl(HEALTH_LOG, data)


# ---------------------------------------------------------------------------
# Autonomy config
# ---------------------------------------------------------------------------

def load_autonomy_config() -> Dict[str, Any]:
    cfg = load_json(AUTONOMY_FILE, default={})
    return cfg if isinstance(cfg, dict) else {}


def get_agent_profile(agent_id: str) -> Dict[str, Any]:
    cfg = load_autonomy_config()
    agents = cfg.get("agents", {})
    profile = agents.get(agent_id, {})
    return profile if isinstance(profile, dict) else {}


# ---------------------------------------------------------------------------
# Events / Rules / Authority
# ---------------------------------------------------------------------------

def load_latest_event() -> Optional[Event]:
    if not EVENTS_FILE.exists():
        print("[GEORGE V2] No events.jsonl found.")
        return None

    last_line = None
    with EVENTS_FILE.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                last_line = line

    if not last_line:
        print("[GEORGE V2] events.jsonl is empty.")
        return None

    try:
        return Event.from_dict(json.loads(last_line))
    except Exception as exc:
        print(f"[GEORGE V2] Failed to parse last event: {exc}", file=sys.stderr)
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
        print("[GEORGE V2] Invalid rules format in george_rules.yaml", file=sys.stderr)
        return []
    return rules


# ---------------------------------------------------------------------------
# Gate / Canonical output builders
# ---------------------------------------------------------------------------

def _gate_trace_alias(decision_trace: Dict[str, Any], dec: Decision) -> Dict[str, Any]:
    """
    Provide `trace` alias, because some systems expect `trace` not `decision_trace`.
    """
    trace_id = decision_trace.get("trace_id") or dec.id
    path = decision_trace.get("execution_path") or decision_trace.get("path") or ["george"]
    return {
        "complete": bool(decision_trace.get("complete", True)),
        "id": trace_id,
        "trace_id": trace_id,
        "path": list(path) if isinstance(path, list) else [str(path)],
        "execution_path": list(path) if isinstance(path, list) else [str(path)],
    }


def _default_execution_context() -> Dict[str, Any]:
    return {
        "latency_ms": 0,
        "dependencies": [],
        "security_context": {"authenticated": True, "authorization_level": "standard"},
    }


def _build_canonical_latest(dec: Decision, health: HealthState) -> Dict[str, Any]:
    # status endpoint ok = status.json readable
    status_ok, _ = _safe_load_status()

    # health score for gate is float 0..1
    health_score = float(health.system_stability_score)

    # decision_trace_present is what runtime_gate.py actually checks
    decision_trace_present = bool(dec.decision_trace) or bool(getattr(dec, "decision_trace", None))

    # guardian_ok used by policies
    guardian_ok = True if dec.guardian_flag in (None, "", "ok") else False

    health_context = dec.health_context or {
        "system_health": int(round(health_score * 100)),  # percent convenience
        "guardian_status": "OK" if guardian_ok else "WARNING",
        "performance_metrics": {
            "agent_response_success_rate": health.agent_response_success_rate,
            "total_actions": health.total_actions,
            "failed_actions": health.failed_actions,
        },
    }

    decision_trace = dec.decision_trace or {
        "complete": True,
        "trace_id": dec.id,
        "execution_path": ["george", "guardian", "authority", "executor"],
    }

    execution_context = dec.execution_context or _default_execution_context()

    # signals block MUST match runtime_gate.py keypaths
    signals = {
        "system_health_score": health_score,                # 0..1 float
        "guardian_ok": bool(guardian_ok),
        "status_endpoint_ok": bool(status_ok),
        "decision_trace_present": bool(decision_trace_present),
        # optional convenience:
        "system_health_percent": int(round(health_score * 100)),
    }

    canonical: Dict[str, Any] = {
        "schema_version": "2.0",
        "decision_id": dec.id,
        "id": dec.id,  # legacy alias
        "timestamp": dec.timestamp,
        "source_event_id": dec.source_event_id,
        "agent": dec.agent,
        "trigger": dec.action,          # legacy-ish, harmless
        "action": dec.action,
        "intent": dec.intent,
        "status": dec.status,
        "confidence": dec.confidence,

        "decision_class": dec.decision_class,
        "authority_source": dec.authority_source,

        "error_message": dec.error_message,
        "guardian_flag": dec.guardian_flag,
        "follow_up": dec.follow_up,
        "result_summary": dec.result_summary,

        "health_context": health_context,
        "decision_trace": decision_trace,
        "trace": _gate_trace_alias(decision_trace, dec),
        "execution_context": execution_context,

        "signals": signals,

        "guardian": {
            "ok": bool(guardian_ok),
            "status": health_context.get("guardian_status"),
            "flag": dec.guardian_flag,
            "recommendation": dec.follow_up,
        },

        # kept for compatibility/debug
        "alternatives_considered": [],
    }
    return canonical


# ---------------------------------------------------------------------------
# Decision persistence
# ---------------------------------------------------------------------------

def save_decision(decision: Decision | Dict[str, Any]) -> None:
    """
    Writes:
      - ops/decisions/latest.json         (runtime_gate input)
      - ops/decisions/canonical_latest.json (stable canonical record)
      - reports + history jsonl
    """
    if isinstance(decision, Decision):
        dec_obj = decision
        dec_dict = decision.to_dict()
    else:
        # minimal fallback object
        dec_dict = dict(decision)
        dec_obj = Decision(
            id=dec_dict.get("id") or dec_dict.get("decision_id") or str(uuid.uuid4()),
            timestamp=dec_dict.get("timestamp") or now_iso(),
            source_event_id=dec_dict.get("source_event_id"),
            agent=dec_dict.get("agent", "unknown"),
            action=dec_dict.get("action", "unknown"),
            intent=dec_dict.get("intent"),
            confidence=float(dec_dict.get("confidence", 0.0)),
            status=dec_dict.get("status", "unknown"),
            error_message=dec_dict.get("error_message"),
            guardian_flag=dec_dict.get("guardian_flag"),
            follow_up=dec_dict.get("follow_up"),
            result_summary=dec_dict.get("result_summary"),
            decision_class=dec_dict.get("decision_class", "operational"),
            authority_source=dec_dict.get("authority_source", "george"),
            health_context=dec_dict.get("health_context"),
            decision_trace=dec_dict.get("decision_trace"),
            execution_context=dec_dict.get("execution_context"),
        )

    # health required to build signals
    health = load_health()

    canonical_latest = _build_canonical_latest(dec_obj, health)

    # logs
    today = datetime.now(timezone.utc).date().isoformat()
    append_jsonl(DECISIONS_LOG, dec_dict)
    history_file = DECISIONS_HISTORY_DIR / f"{today}.jsonl"
    append_jsonl(history_file, dec_dict)

    # write canonical + gate input
    save_json(CANONICAL_LATEST, canonical_latest)
    save_json(DECISIONS_LATEST, canonical_latest)

    update_snapshot(today, dec_dict)


def update_snapshot(date: str, decision: Dict[str, Any]) -> None:
    snapshot_path = DECISIONS_SNAPSHOTS_DIR / f"{date}.json"

    if snapshot_path.exists():
        try:
            with snapshot_path.open("r", encoding="utf-8") as f:
                snapshot = json.load(f)
        except json.JSONDecodeError:
            print(f"[GEORGE V2] Snapshot corrupt, re-init: {snapshot_path}", file=sys.stderr)
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
# Orchestration helpers
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
    Must match runtime_gate.py policy decision_classes keys:
      safety_critical | operational | strategic | deploy
    """
    if rule:
        then_cfg = rule.get("then", {}) or {}
        dc = then_cfg.get("decision_class")
        if dc:
            dc = str(dc).lower().strip()
            if dc in {"critical", "safety", "safety-critical", "safetycritical"}:
                return "safety_critical"
            if dc in {"ops", "operation"}:
                return "operational"
            return dc

    if event.intent:
        dc = str(event.intent).lower().strip()
        if dc in {"critical", "safety", "safety-critical", "safetycritical"}:
            return "safety_critical"
        return dc

    return "operational"


def guardian_precheck(
    decision: Decision,
    agent_profile: Dict[str, Any],
    rule: Optional[Dict[str, Any]] = None,
) -> Tuple[bool, Optional[str]]:
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
) -> Tuple[bool, Optional[str], Optional[str], str]:
    """
    Returns: (allowed, block_reason, required_authority, decision_class)
    """
    matrix = load_authority_matrix()
    decision_class = resolve_decision_class(event, rule)

    default_cfg = (matrix.get("default") or {}) if isinstance(matrix.get("default"), dict) else {}
    classes_cfg = (matrix.get("classes") or {}) if isinstance(matrix.get("classes"), dict) else {}
    agents_cfg = (matrix.get("agents") or {}) if isinstance(matrix.get("agents"), dict) else {}

    class_cfg = (classes_cfg.get(decision_class) or {}) if isinstance(classes_cfg.get(decision_class), dict) else {}
    required = str(class_cfg.get("require") or default_cfg.get("require") or "human").lower()

    agent_id = decision.agent
    agent_override = agents_cfg.get(agent_id, {}) if isinstance(agents_cfg.get(agent_id), dict) else {}
    allowed_classes = agent_override.get("allowed_classes")
    if isinstance(allowed_classes, list) and decision_class not in [str(x).lower() for x in allowed_classes]:
        return False, "agent_not_allowed_for_decision_class", "human", decision_class

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
# Main orchestration
# ---------------------------------------------------------------------------

def orchestrate() -> Optional[Decision]:
    if emergency_lock_active():
        append_trace({
            "actor": "george_v2",
            "phase": "emergency_lock",
            "result": "stopped",
            "reason": "emergency_lock_active",
        })
        print("[GEORGE V2] Emergency Lock active – stopped.", file=sys.stderr)
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

    # Guardian precheck
    allowed, guardian_flag = guardian_precheck(decision, target_profile, rule)
    if not allowed:
        decision.status = "blocked"
        decision.guardian_flag = guardian_flag or "blocked_by_guardian"
        decision.authority_source = "guardian"

        # Attach minimal trace so gate can see trace presence as true
        decision.decision_trace = {
            "complete": True,
            "trace_id": decision.id,
            "execution_path": ["george", "guardian"],
        }
        decision.execution_context = _default_execution_context()

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

        print(f"[GEORGE V2] Decision {decision.id} BLOCKED by Guardian: {decision.guardian_flag}")
        return decision

    append_trace({
        "actor": "guardian",
        "phase": "precheck",
        "decision_id": decision.id,
        "result": "allowed",
        "target_agent": target_agent,
        "action": action,
    })

    # Authority enforcement
    allowed_auth, reason, required, decision_class = authority_enforcement(decision, event, target_profile, rule)
    decision.decision_class = decision_class

    if not allowed_auth:
        decision.status = "blocked"
        decision.guardian_flag = reason or "blocked_by_authority"
        decision.follow_up = f"Requires approval: {required}" if required else "Requires approval"
        decision.authority_source = "human" if required else "guardian"

        decision.decision_trace = {
            "complete": True,
            "trace_id": decision.id,
            "execution_path": ["george", "guardian", "authority"],
        }
        decision.execution_context = _default_execution_context()

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

    # Execute (simulated)
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

    # Health + postcheck
    health = load_health()
    guardian_flag_post = guardian_postcheck(decision, target_profile or {}, health, success)
    if guardian_flag_post:
        decision.guardian_flag = guardian_flag_post

    save_health(health)

    # Attach gate contexts BEFORE saving decision
    guardian_ok = True if decision.guardian_flag in (None, "", "ok") else False

    decision.health_context = {
        "system_health": int(round(health.system_stability_score * 100)),
        "guardian_status": "OK" if guardian_ok else "WARNING",
        "performance_metrics": {
            "agent_response_success_rate": health.agent_response_success_rate,
            "total_actions": health.total_actions,
            "failed_actions": health.failed_actions,
        },
    }
    decision.decision_trace = {
        "complete": True,
        "trace_id": decision.id,
        "execution_path": ["george", "guardian", "authority", "executor"],
    }
    decision.execution_context = _default_execution_context()

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
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    decision = orchestrate()
    if not decision:
        print("[GEORGE V2] No decision made (no event or emergency lock active).")
    else:
        print(
            f"[GEORGE V2] Done – Decision {decision.id} -> {decision.status}, "
            f"guardian_flag={decision.guardian_flag!r}"
        )


if __name__ == "__main__":
    main()
