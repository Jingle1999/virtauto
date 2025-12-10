#!/usr/bin/env python3
"""
content_creator Agent v1 – Governor für Inhalte

Ziele v1:
- Laufende Präsenz in status/status.json
- Content-Vorschläge als Markdown-Report
- Keine direkten Änderungen an der Website, nur Vorschläge
"""

from pathlib import Path
from datetime import datetime, timezone
import json

STATUS_FILE = Path("status/status.json")
REPORT_FILE = Path("status/content_suggestions.md")

AGENT_ID = "content_creator"
AGENT_TITLE = "Content Governor Agent v1"


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


def upsert_agent_status(data: dict, agent_id: str, status: str, topics: list[dict] | None = None) -> dict:
    agents = [a for a in data.get("agents", []) if a.get("agent") != agent_id]
    entry: dict = {
        "agent": agent_id,
        "status": status,
        "timestamp": now_iso(),
    }
    if topics:
        entry["topics"] = topics
    agents.append(entry)
    data["agents"] = agents
    return data


def build_suggestions() -> list[dict]:
    """
    v1: Statische, aber sinnvolle Vorschläge.
    Später können wir hier echte Analysen (z.B. Filesystem-Scan, RAG, etc.) einbauen.
    """
    suggestions: list[dict] = []

    # A) Überschriften / Klarheit
    suggestions.append({
        "area": "Homepage",
        "type": "headline",
        "action": "review",
        "description": "Clarify the main value proposition of virtauto.OS for OEMs in one sentence.",
    })

    # B) Lücken / dünne Inhalte
    suggestions.append({
        "area": "Agents Page",
        "type": "content_gap",
        "action": "extend",
        "description": "Add short, concrete examples for each agent (Guardian, Monitoring, Deploy, Content).",
    })

    # C) Neue Seitenideen
    suggestions.append({
        "area": "New Page",
        "type": "idea",
        "action": "create",
        "description": "Create a 'How GEORGE works' page explaining orchestration, autonomy and self-healing.",
    })

    # D) LinkedIn-Posts
    suggestions.append({
        "area": "LinkedIn",
        "type": "social",
        "action": "draft",
        "description": "Prepare a post about stabilizing GEORGE and the next step towards 70–80% autonomy.",
    })

    # E) Changelog
    suggestions.append({
        "area": "Changelog",
        "type": "log",
        "action": "update",
        "description": "Record today's GEORGE v2 orchestration and health improvements as part of the public changelog.",
    })

    return suggestions


def write_report(topics: list[dict]) -> None:
    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# {AGENT_TITLE} – Suggestions",
        "",
        f"Generated at: {now_iso()}",
        "",
        "## Suggested topics",
        "",
    ]
    for t in topics:
        lines.append(
            f"- **[{t.get('area')}]** ({t.get('type')}/{t.get('action')}): {t.get('description')}"
        )
    REPORT_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    status = load_status()
    topics = build_suggestions()
    status = upsert_agent_status(status, AGENT_ID, status="ok", topics=topics)
    save_status(status)
    write_report(topics)


if __name__ == "__main__":
    main()
