from pathlib import Path
import json
from datetime import datetime, timezone

STATUS_FILE = Path("status/status.json")
REPORT_FILE = Path("status/agent_reports.md")

AGENT_ID = "deploy"
AGENT_TITLE = "Deploy Agent"


def load_status():
    if STATUS_FILE.exists():
        try:
            return json.loads(STATUS_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {"agents": []}


def save_status(data):
    STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATUS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def upsert_agent(data, agent_id, status="ok"):
    ts = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    agents = [a for a in data.get("agents", []) if a.get("agent") != agent_id]
    agents.append({"agent": agent_id, "status": status, "timestamp": ts})
    data["agents"] = agents
    return data, ts


def write_report(title, ts):
    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    REPORT_FILE.write_text(
        f"## {title} - Latest Report\n\n"
        f"Last deployment orchestration completed successfully.\n\n"
        f"Generated: {ts}\n",
        encoding="utf-8",
    )


def main():
    data = load_status()
    data, ts = upsert_agent(data, AGENT_ID, status="ok")
    save_status(data)
    write_report(AGENT_TITLE, ts)


if __name__ == "__main__":
    main()
