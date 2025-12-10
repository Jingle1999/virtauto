#!/usr/bin/env python3
"""
Deploy Agent v1 – simulated deploy + healthcheck + rollback hint

Ziel (Option 3):
- "Deploy" durchführen (v1: nur simuliert)
- Health-Check ausführen
- Bei schlechter Health Rollback empfehlen
- Status-File und Report aktualisieren
"""

from pathlib import Path
from datetime import datetime, timezone
import json

STATUS_FILE = Path("status/status.json")
REPORT_FILE = Path("status/deploy_agent_report.md")

AGENT_ID = "deploy"
AGENT_TITLE = "Deploy Agent v1"


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_status() -> dict:
    if STATUS_FILE.exists():
        try:
            return json.loads(STATUS_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {"agents": []}


def save_status(data: dict) -> None:
    STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATUS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def upsert_agent_status(data: dict, agent_id: str, status: str, details: dict | None = None) -> dict:
    agents = [a for a in data.get("agents", []) if a.get("agent") != agent_id]
    entry = {
        "agent": agent_id,
        "status": status,
        "timestamp": now_iso(),
    }
    if details:
        entry["details"] = details
    agents.append(entry)
    data["agents"] = agents
    return data


# --- v1: Simulierte Deploy-/Health-Logik -----------------------------------


def simulate_deploy() -> dict:
    """
    v1: kein echtes Deploy, sondern nur ein simulierter Erfolg.
    Später kann hier ein echter CI/CD-Trigger eingebaut werden.
    """
    return {
        "result": "simulated_deploy_ok",
        "target": "virtauto.de",
        "environment": "production",
    }


def simulate_healthcheck() -> dict:
    """
    v1: Health wird hart auf 'ok' gesetzt – später echte Checks (Ping, Statusseite etc.).
    """
    return {
        "status": "ok",
        "health_score": 0.95,
        "notes": "Simulated healthcheck – v1 baseline.",
    }


def evaluate_rollback(health: dict) -> dict:
    """
    Option 3: Deploy + Healthcheck + (v1) Rollback-Empfehlung.
    Wir empfehlen Rollback, wenn health_score < 0.8.
    """
    score = float(health.get("health_score", 0.0))
    needs_rollback = score < 0.8
    return {
        "health_score": score,
        "needs_rollback": needs_rollback,
        "reason": (
            "Health below threshold, rollback recommended."
            if needs_rollback
            else "Health within acceptable range, no rollback required."
        ),
    }


def write_report(deploy_info: dict, health_info: dict, rollback_info: dict) -> None:
    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    REPORT_FILE.write_text(
        (
            f"# {AGENT_TITLE} – Latest Run\n\n"
            f"- Timestamp: {now_iso()}\n"
            f"- Deploy result: {deploy_info.get('result')}\n"
            f"- Target: {deploy_info.get('target')} ({deploy_info.get('environment')})\n\n"
            f"## Healthcheck\n"
            f"- Status: {health_info.get('status')}\n"
            f"- Health Score: {health_info.get('health_score')}\n"
            f"- Notes: {health_info.get('notes')}\n\n"
            f"## Rollback Evaluation\n"
            f"- Needs rollback: {rollback_info.get('needs_rollback')}\n"
            f"- Reason: {rollback_info.get('reason')}\n"
        ),
        encoding="utf-8",
    )


def main() -> None:
    # 1) Status laden
    status = load_status()

    # 2) Simuliertes Deploy
    deploy_info = simulate_deploy()

    # 3) Simulierter Healthcheck
    health_info = simulate_healthcheck()

    # 4) Rollback-Empfehlung berechnen
    rollback_info = evaluate_rollback(health_info)

    # 5) Agentenstatus bestimmen
    agent_status = "degraded" if rollback_info["needs_rollback"] else "ok"

    # 6) Status aktualisieren
    status = upsert_agent_status(
        status,
        AGENT_ID,
        status=agent_status,
        details={
            "deploy": deploy_info,
            "health": health_info,
            "rollback": rollback_info,
        },
    )
    save_status(status)

    # 7) Report schreiben
    write_report(deploy_info, health_info, rollback_info)


if __name__ == "__main__":
    main()
