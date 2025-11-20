from pathlib import Path
import json
from datetime import datetime, timezone

# Repo-Root: .../virtauto
ROOT = Path(__file__).resolve().parents[1]
STATUS_DIR = ROOT / "status"
STATUS_FILE = STATUS_DIR / "status.json"
GEORGE_LOG = STATUS_DIR / "george.log"

def load_status():
    if not STATUS_FILE.exists():
        return {"agents": []}
    try:
        with STATUS_FILE.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        # Fallback, falls die Datei kaputt ist
        return {"agents": []}

def summarize_agents(status_data):
    agents = status_data.get("agents", [])
    now = datetime.now(timezone.utc)

    lines = []
    lines.append("# GEORGE Orchestrator – Agent Summary")
    lines.append(f"Generated: {now.isoformat()}")
    lines.append("")

    if not agents:
        lines.append("_No agent status information available yet._")
        return "\n".join(lines)

    lines.append("## Agents")
    for agent in agents:
        name = agent.get("agent", "unknown")
        st = agent.get("status", "unknown")
        ts = agent.get("timestamp", "n/a")
        lines.append(f"- **{name}** → status: `{st}`, last update: `{ts}`")

    lines.append("")
    lines.append(
        "_GEORGE currently only observes and summarizes agent health. "
        "Next step: use these signals to trigger additional workflows._"
    )

    return "\n".join(lines)

def main():
    STATUS_DIR.mkdir(parents=True, exist_ok=True)

    status_data = load_status()
    report = summarize_agents(status_data)

    with GEORGE_LOG.open("w", encoding="utf-8") as f:
        f.write(report)

if __name__ == "__main__":
    main()
