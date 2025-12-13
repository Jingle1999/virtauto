from pathlib import Path
import json
from datetime import datetime, timezone
import sys
import subprocess

# Robust base paths (no dependence on current working directory)
OPS_DIR = Path(__file__).resolve().parent
REPO_ROOT = OPS_DIR.parent
HEALTH_DASHBOARD = OPS_DIR / "health_dashboard.py"
STATUS_FILE = REPO_ROOT / "status" / "status.json"
REPORT_FILE = REPO_ROOT / "status" / "agent_reports.md"

AGENT_ID = "monitoring"
AGENT_TITLE = "Monitoring Agent"

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
        f"Basic heartbeat check succeeded.\n\n"
        f"Generated: {ts}\n",
        encoding="utf-8",
    )

def trigger_health_dashboard():
    """
    Run ops/health_dashboard.py in a robust way:
    - uses current Python interpreter (sys.executable)
    - uses absolute script path
    - runs with repo root as cwd (so relative paths in health_dashboard keep working)
    - never crashes this agent (check=False), but prints stderr for visibility
    """
    if not HEALTH_DASHBOARD.exists():
        print(f"[monitoring_agent] health_dashboard.py not found: {HEALTH_DASHBOARD}")
        return

    try:
        res = subprocess.run(
            [sys.executable, str(HEALTH_DASHBOARD)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            check=False
            timeout=60
        )
        if res.returncode != 0:
            print("[monitoring_agent] health_dashboard trigger failed:")
            if res.stdout:
                print(res.stdout[-2000:])
            if res.stderr:
                print(res.stderr[-2000:])
    except Exception as e:
        print(f"[monitoring_agent] health_dashboard trigger exception: {e}")

def main():
    data = load_status()
    data, ts = upsert_agent(data, AGENT_ID, status="ok")
    save_status(data)

    trigger_health_dashboard()

    write_report(AGENT_TITLE, ts)

if __name__ == "__main__":
    main()
