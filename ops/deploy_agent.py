#!/usr/bin/env python3
"""
Deploy Agent – Simulation Only (authoritative: ops/reports/system_status.json)

Rules:
- Never triggers a real deploy.
- Produces a deploy plan + report artifacts.
- Updates agents.deploy in ops/reports/system_status.json
- Enforces emergency lock (ops/emergency_lock.json) as hard stop.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


ROOT = Path(__file__).resolve().parents[1]  # repo root
STATUS_FILE = ROOT / "ops" / "reports" / "system_status.json"
EVENTS_FILE = ROOT / "ops" / "events.jsonl"
EMERGENCY_LOCK_FILE = ROOT / "ops" / "emergency_lock.json"

REPORT_DIR = ROOT / "ops" / "reports"
DEPLOY_REPORT = REPORT_DIR / "deploy_agent_report.md"
DEPLOY_PLAN = REPORT_DIR / "deploy_plan.json"

AGENT_ID = "deploy"
AGENT_ROLE = "deployment_agent"
MODE = "simulation_only"

DEFAULT_HEALTH_MIN_SCORE = 0.70


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def read_last_event(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    try:
        lines = [ln.strip() for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
        if not lines:
            return None
        return json.loads(lines[-1])
    except Exception:
        return None


def is_emergency_locked() -> bool:
    if not EMERGENCY_LOCK_FILE.exists():
        return False
    try:
        data = read_json(EMERGENCY_LOCK_FILE)
        return bool(data.get("locked", False))
    except Exception:
        # fail-safe: treat as locked if unreadable
        return True


def ensure_status_minimal(status: Dict[str, Any]) -> Dict[str, Any]:
    if not status:
        status = {
            "version": "1.0",
            "generated_at": now_iso(),
            "source": "deploy_agent",
            "environment": "production",
            "system_state": {"status": "online", "mode": "stabilization"},
            "health": {"overall_score": 0.0, "signal": "unknown", "metrics": {}},
            "agents": {},
            "policy": {
                "deploy_requires_human_approval": True,
                "hard_stop": {
                    "health_min_score": DEFAULT_HEALTH_MIN_SCORE,
                    "require_system_online": True,
                    "require_self_guardian_green": True,
                },
            },
        }
    if not isinstance(status.get("agents"), dict):
        status["agents"] = {}
    if not isinstance(status.get("policy"), dict):
        status["policy"] = {}
    if not isinstance(status.get("system_state"), dict):
        status["system_state"] = {"status": "online", "mode": "stabilization"}
    if not isinstance(status.get("health"), dict):
        status["health"] = {"overall_score": 0.0, "signal": "unknown", "metrics": {}}
    return status


@dataclass
class Policy:
    deploy_requires_human_approval: bool
    health_min_score: float
    require_system_online: bool
    require_self_guardian_green: bool


def load_policy(status: Dict[str, Any]) -> Policy:
    policy = status.get("policy", {}) if isinstance(status.get("policy"), dict) else {}
    hard = policy.get("hard_stop", {}) if isinstance(policy.get("hard_stop"), dict) else {}

    return Policy(
        deploy_requires_human_approval=bool(policy.get("deploy_requires_human_approval", True)),
        health_min_score=float(hard.get("health_min_score", DEFAULT_HEALTH_MIN_SCORE)),
        require_system_online=bool(hard.get("require_system_online", True)),
        require_self_guardian_green=bool(hard.get("require_self_guardian_green", True)),
    )


def get_guardian_health(status: Dict[str, Any]) -> str:
    agents = status.get("agents", {})
    guardian = agents.get("guardian", {}) if isinstance(agents, dict) else {}
    if isinstance(guardian, dict):
        return str(guardian.get("health", "")).lower()
    return ""


def get_deployment_gate(status: Dict[str, Any]) -> Dict[str, Any]:
    agents = status.get("agents", {})
    if not isinstance(agents, dict):
        return {}
    dep = agents.get("deployment", {})
    return dep if isinstance(dep, dict) else {}


def checks(status: Dict[str, Any], policy: Policy) -> Dict[str, Dict[str, Any]]:
    sys_state = status.get("system_state", {})
    sys_status = str((sys_state or {}).get("status", "")).lower()

    health = status.get("health", {})
    health_score = float((health or {}).get("overall_score", 0.0))

    guardian_health = get_guardian_health(status)

    deployment_gate = get_deployment_gate(status)
    human_approved = bool(deployment_gate.get("human_approved", False))

    out: Dict[str, Dict[str, Any]] = {}

    out["system_online"] = {
        "ok": (sys_status == "online") if policy.require_system_online else True,
        "reason": f"system_state.status='{sys_status}'",
    }
    out["guardian_green"] = {
        "ok": (guardian_health == "green") if policy.require_self_guardian_green else True,
        "reason": f"guardian.health='{guardian_health}'",
    }
    out["health_threshold"] = {
        "ok": health_score >= policy.health_min_score,
        "reason": f"health.overall_score={health_score:.2f} (min {policy.health_min_score:.2f})",
    }
    out["human_approval"] = {
        # For REAL deploy readiness. We still run simulation regardless.
        "ok": (human_approved is True) or (policy.deploy_requires_human_approval is False),
        "reason": f"deployment.human_approved={human_approved}, requires={policy.deploy_requires_human_approval}",
    }

    return out


def build_plan(status: Dict[str, Any], last_event: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    sys_state = status.get("system_state", {}) or {}
    return {
        "generated_at": now_iso(),
        "agent": AGENT_ID,
        "mode": MODE,
        "environment": status.get("environment", "production"),
        "system_mode": sys_state.get("mode", "stabilization"),
        "trigger_event": last_event,
        "actions": [
            {"type": "readiness_check", "source": "ops/reports/system_status.json"},
            {"type": "simulate_deploy", "note": "No workflow dispatch performed by deploy agent."},
            {"type": "simulate_post_deploy_healthcheck", "note": "No external calls in skeleton."},
        ],
        "safety": {
            "real_deploy_executed": False,
            "human_approval_required_for_real_deploy": True,
        },
    }


def write_report(policy: Policy, check_map: Dict[str, Dict[str, Any]], readiness_ok: bool) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    lines = []
    lines.append("# Deploy Agent Report (Simulation Only)\n")
    lines.append(f"- Timestamp: `{now_iso()}`")
    lines.append(f"- Readiness for real deploy: `{'READY' if readiness_ok else 'BLOCKED'}`")
    lines.append("")
    lines.append("## Policy")
    lines.append(f"- deploy_requires_human_approval: `{policy.deploy_requires_human_approval}`")
    lines.append(f"- health_min_score: `{policy.health_min_score}`")
    lines.append(f"- require_system_online: `{policy.require_system_online}`")
    lines.append(f"- require_self_guardian_green: `{policy.require_self_guardian_green}`")
    lines.append("")
    lines.append("## Checks")
    for k, v in check_map.items():
        lines.append(f"- {'✅' if v['ok'] else '❌'} **{k}** — {v['reason']}")
    lines.append("")
    lines.append("## Safety")
    lines.append("- No real deployment is executed by this agent.")
    lines.append("- This agent only creates artifacts and updates system_status.json.")
    DEPLOY_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def upsert_agents_deploy(status: Dict[str, Any], patch: Dict[str, Any]) -> None:
    agents = status.setdefault("agents", {})
    if not isinstance(agents, dict):
        agents = {}
        status["agents"] = agents
    cur = agents.get(AGENT_ID, {})
    if not isinstance(cur, dict):
        cur = {}
    cur.update(patch)
    agents[AGENT_ID] = cur


def main() -> int:
    if is_emergency_locked():
        # Hard stop
        raise SystemExit("EMERGENCY LOCK active. Aborting deploy agent (simulation).")

    status = ensure_status_minimal(read_json(STATUS_FILE))
    policy = load_policy(status)

    last_event = read_last_event(EVENTS_FILE)
    check_map = checks(status, policy)

    # readiness for a REAL deploy (we still do simulation only)
    readiness_ok = all([
        check_map["system_online"]["ok"],
        check_map["guardian_green"]["ok"],
        check_map["health_threshold"]["ok"],
        check_map["human_approval"]["ok"],
    ])

    # artifacts
    plan = build_plan(status, last_event)
    write_json(DEPLOY_PLAN, plan)
    write_report(policy, check_map, readiness_ok)

    # update authoritative status
    upsert_agents_deploy(status, {
        "status": "ready" if readiness_ok else "blocked",
        "role": AGENT_ROLE,
        "health": "green" if readiness_ok else "yellow",
        "mode": MODE,
        "last_action": "simulate_deploy_plan",
        "last_request": (last_event.get("type") if isinstance(last_event, dict) else None),
        "timestamp": now_iso(),
        "details": {
            "readiness_ok": readiness_ok,
            "checks": check_map,
            "artifacts": {
                "deploy_plan": str(DEPLOY_PLAN.relative_to(ROOT)),
                "deploy_report": str(DEPLOY_REPORT.relative_to(ROOT)),
            },
        },
    })

    status["generated_at"] = now_iso()
    status["source"] = "deploy_agent"
    write_json(STATUS_FILE, status)

    # 0 = ready, 2 = blocked (but simulation succeeded)
    return 0 if readiness_ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
