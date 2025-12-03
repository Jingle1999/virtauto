#!/usr/bin/env python3
"""
GEORGE Orchestrator V1.0

- Liest das zuletzt eingetragene Event aus ops/events.jsonl
- Lädt Orchestrierungsregeln aus ops/rules/george_rules.yaml
- Wendet passende Regeln an
- Schreibt neue "GEORGE-Aktionen" als Events zurück nach ops/events.jsonl

Dieses Skript ist bewusst einfach gehalten:
- verarbeitet immer nur das letzte Event
- erzeugt pro zutreffender Regel genau ein Folge-Event
"""

import datetime
import json
import pathlib
from typing import Any, Dict, List, Optional

import yaml  # PyYAML


# Pfade relativ zum Repo-Root bestimmen
ROOT = pathlib.Path(__file__).resolve().parents[1]
EVENTS_FILE = ROOT / "ops" / "events.jsonl"
RULES_FILE = ROOT / "ops" / "rules" / "george_rules.yaml"


def now_iso() -> str:
    """UTC-Zeit als ISO-String (ohne Mikrosekunden)."""
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def load_rules() -> List[Dict[str, Any]]:
    """Lädt die Orchestrierungsregeln aus george_rules.yaml."""
    if not RULES_FILE.exists():
        raise FileNotFoundError(f"Rules file not found: {RULES_FILE}")

    with RULES_FILE.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    rules = data.get("rules", [])
    if not isinstance(rules, list):
        raise ValueError("george_rules.yaml: 'rules' muss eine Liste sein.")
    return rules


def load_latest_event() -> Optional[Dict[str, Any]]:
    """Liest das letzte Event aus events.json (JSON-Array)."""
    if not EVENTS_FILE.exists():
        return None

    try:
        with EVENTS_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError:
        print("Warnung: events.json ist kein gültiges JSON.")
        return None

    if not isinstance(data, list) or not data:
        return None

    return data[-1]  # last event in Array


def _normalize_to_list(value: Any) -> List[Any]:
    """Hilfsfunktion: akzeptiert Single-Value oder Liste und gibt immer Liste zurück."""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def rule_matches(event: Dict[str, Any], rule: Dict[str, Any]) -> bool:
    """Prüft, ob eine Regel auf ein Event passt."""
    match = rule.get("match", {})
    if not isinstance(match, dict):
        return False

    rule_agents = _normalize_to_list(match.get("agent"))
    rule_events = _normalize_to_list(match.get("event"))

    ev_agent = event.get("agent")
    ev_event = event.get("event")

    # Agent-Match (falls angegeben)
    if rule_agents and ev_agent not in rule_agents:
        return False

    # Event-Match (falls angegeben)
    if rule_events and ev_event not in rule_events:
        return False

    return True


def build_follow_up_events(
    source_event: Dict[str, Any], rules: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Erzeugt neue Events für alle Regeln, die auf das Source-Event matchen."""

    follow_ups: List[Dict[str, Any]] = []

    for rule in rules:
        if not rule_matches(source_event, rule):
            continue

        action = rule.get("action", {})
        target_agent = action.get("target_agent")
        intent = action.get("intent")
        message = action.get("message")

        if not target_agent:
            # Regel ohne Zielagenten ignorieren
            continue

        follow_event: Dict[str, Any] = {
            "timestamp": now_iso(),
            "agent": "george",  # GEORGE selbst
            "event": "route",
            "rule_id": rule.get("id"),
            "source_agent": source_event.get("agent"),
            "source_event": source_event.get("event"),
            "target_agent": target_agent,
            "intent": intent,
            "message": message,
        }

        follow_ups.append(follow_event)

    return follow_ups


def append_events(events: List[Dict[str, Any]]) -> None:
    """Hängt neue Events an events.json (JSON-Array) an."""
    if not events:
        return

    existing: List[Dict[str, Any]] = []
    if EVENTS_FILE.exists():
        try:
            with EVENTS_FILE.open("r", encoding="utf-8") as f:
                existing = json.load(f)
        except json.JSONDecodeError:
            print("Warnung: Konnte bestehende events.json nicht lesen – starte mit leerem Array.")
            existing = []

    if not isinstance(existing, list):
        existing = []

    existing.extend(events)

    with EVENTS_FILE.open("w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False)



def main() -> None:
    print("GEORGE Orchestrator V1.0 starting…")

    latest_event = load_latest_event()
    if not latest_event:
        print("Keine Events gefunden – nichts zu tun.")
        return

    print(f"Letztes Event: agent={latest_event.get('agent')} "
          f"event={latest_event.get('event')}")

    try:
        rules = load_rules()
    except Exception as exc:
        print(f"Fehler beim Laden der Regeln: {exc}")
        return

    follow_ups = build_follow_up_events(latest_event, rules)

    if not follow_ups:
        print("GEORGE: Keine passenden Regeln – No-Op.")
        return

    append_events(follow_ups)
    print(f"GEORGE: {len(follow_ups)} Folge-Event(s) erzeugt und gespeichert.")
    for ev in follow_ups:
        print(
            f"  → rule={ev.get('rule_id')} "
            f"source={ev.get('source_agent')}/{ev.get('source_event')} "
            f"target={ev.get('target_agent')} intent={ev.get('intent')}"
        )


if __name__ == "__main__":
    main()
