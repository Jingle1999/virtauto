# tests/test_george_orchestrator_v2.py
"""
Tests für GEORGE Orchestrator V2 – Autonomie, Health & Persistenz.

Voraussetzungen:
- ops/george_orchestrator_v2.py existiert
- ops/autonomy.json existiert
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any, Dict

import pytest


# ---------------------------------------------------------------------------
# Import des GEORGE V2 Moduls
# ---------------------------------------------------------------------------

try:
    import ops.george_orchestrator_v2 as george_v2
except ModuleNotFoundError as exc:  # pragma: no cover - harte Fehlkonfiguration
    pytest.skip(f"Konnte ops.george_orchestrator_v2 nicht importieren: {exc}", allow_module_level=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _assert_float_between(value: float, low: float, high: float, label: str) -> None:
    assert low <= value <= high, f"{label} sollte zwischen {low} und {high} liegen, ist aber {value}"


# ---------------------------------------------------------------------------
# Tests: Autonomie-Konfiguration (autonomy.json)
# ---------------------------------------------------------------------------

def test_load_autonomy_config_structure() -> None:
    """autonomy.json muss 'overview' und 'agents' enthalten."""
    cfg = george_v2.load_autonomy_config()

    assert isinstance(cfg, dict), "Autonomie-Konfiguration muss ein Dict sein"
    assert "overview" in cfg, "Key 'overview' fehlt in autonomy.json"
    assert "agents" in cfg, "Key 'agents' fehlt in autonomy.json"

    overview = cfg["overview"]
    assert "system_autonomy_level" in overview
    assert "target_autonomy_level" in overview
    _assert_float_between(
        float(overview["system_autonomy_level"]), 0.0, 1.0, "system_autonomy_level"
    )
    _assert_float_between(
        float(overview["target_autonomy_level"]), 0.0, 1.0, "target_autonomy_level"
    )

    agents = cfg["agents"]
    assert isinstance(agents, dict)
    # Mindestens die Kern-Agenten sollten definiert sein
    for agent_id in ["george", "guardian", "monitoring", "content"]:
        assert (
            agent_id in agents
        ), f"Agent '{agent_id}' sollte in autonomy.json unter 'agents' definiert sein"


@pytest.mark.parametrize("agent_id", ["george", "guardian", "monitoring", "content"])
def test_get_agent_profile_has_minimal_shape(agent_id: str) -> None:
    """
    get_agent_profile(agent_id) muss ein sinnvolles Profil liefern:

    {
      "status": "active" | "planned" | ...,
      "autonomy": float,
      "role": str,
      "actions": list,
      "failure_thresholds": dict
    }
    """
    profile: Dict[str, Any] = george_v2.get_agent_profile(agent_id)

    assert isinstance(profile, dict), "Agent-Profil muss ein Dict sein"
    assert profile.get("status") in {"active", "planned", "paused", "inactive"}
    _assert_float_between(float(profile.get("autonomy", 0.0)), 0.0, 1.0, "autonomy")
    assert isinstance(profile.get("role"), str)
    assert isinstance(profile.get("actions"), list)
    assert isinstance(profile.get("failure_thresholds"), dict)


def test_get_agent_profile_unknown_agent_returns_empty_dict() -> None:
    """Unbekannter Agent sollte ein leeres Dict (oder sehr schlankes Profil) liefern, nicht crashen."""
    profile = george_v2.get_agent_profile("unknown-agent-xyz")
    assert isinstance(profile, dict)
    # Nicht streng validieren – Hauptsache: kein harter Fehler und kein kompletter Unsinn
    assert profile == {} or profile.get("status") in {"inactive", "unknown", None}


# ---------------------------------------------------------------------------
# Tests: HealthState – Selbstheilung / Stabilität
# ---------------------------------------------------------------------------

def test_health_state_register_results_and_ranges() -> None:
    """HealthState.register_result muss Kennzahlen sinnvoll updaten und in [0,1] halten."""
    hs = george_v2.HealthState()

    # Anfangszustand
    assert hs.total_actions == 0
    assert hs.failed_actions == 0
    _assert_float_between(hs.agent_response_success_rate, 0.0, 1.0, "initial success rate")
    _assert_float_between(hs.system_stability_score, 0.0, 1.0, "initial stability")
    _assert_float_between(hs.autonomy_level_estimate, 0.0, 1.0, "initial autonomy")

    # Zwei erfolgreiche Aktionen
    hs.register_result(True)
    hs.register_result(True)

    assert hs.total_actions == 2
    assert hs.failed_actions == 0
    _assert_float_between(hs.agent_response_success_rate, 0.5, 1.0, "success rate nach Erfolgen")
    _assert_float_between(hs.system_stability_score, 0.0, 1.0, "stability nach Erfolgen")
    _assert_float_between(hs.autonomy_level_estimate, 0.4, 1.0, "autonomy nach Erfolgen")

    # Ein Fehler
    hs.register_result(False)

    assert hs.total_actions == 3
    assert hs.failed_actions == 1
    assert hs.self_detection_errors >= 1
    _assert_float_between(hs.agent_response_success_rate, 0.0, 1.0, "success rate nach Fehler")
    _assert_float_between(hs.system_stability_score, 0.0, 1.0, "stability nach Fehler")
    _assert_float_between(hs.autonomy_level_estimate, 0.0, 1.0, "autonomy nach Fehler")


def test_health_state_from_dict_roundtrip() -> None:
    """HealthState.from_dict und to_dict sollten konsistent sein."""
    original = george_v2.HealthState(
        agent_response_success_rate=0.8,
        last_autonomous_action="test_action",
        self_detection_errors=2,
        system_stability_score=0.7,
        autonomy_level_estimate=0.75,
        total_actions=10,
        failed_actions=2,
    )

    data = original.to_dict()
    reconstructed = george_v2.HealthState.from_dict(data)

    assert reconstructed.agent_response_success_rate == pytest.approx(0.8)
    assert reconstructed.last_autonomous_action == "test_action"
    assert reconstructed.self_detection_errors == 2
    assert reconstructed.system_stability_score == pytest.approx(0.7)
    assert reconstructed.autonomy_level_estimate == pytest.approx(0.75)
    assert reconstructed.total_actions == 10
    assert reconstructed.failed_actions == 2


# ---------------------------------------------------------------------------
# Tests: Persistenz von Decisions (History + Snapshots)
# ---------------------------------------------------------------------------

def test_save_decision_writes_history_latest_and_snapshot(tmp_path, monkeypatch) -> None:
    """
    save_decision() muss:
      - in history/DATE.jsonl schreiben
      - latest.json aktualisieren
      - snapshots/DATE.json aktualisieren
    Wir patchen dazu alle DECISIONS_* Pfade in ein temporäres Verzeichnis.
    """
    # Pfade ins Temp-Verzeichnis umlenken
    decisions_dir = tmp_path / "decisions"
    history_dir = decisions_dir / "history"
    snapshots_dir = decisions_dir / "snapshots"
    latest_file = decisions_dir / "latest.json"

    # Monkeypatch der Modulkonstanten
    monkeypatch.setattr(george_v2, "DECISIONS_DIR", decisions_dir, raising=False)
    monkeypatch.setattr(george_v2, "DECISIONS_HISTORY_DIR", history_dir, raising=False)
    monkeypatch.setattr(george_v2, "DECISIONS_SNAPSHOTS_DIR", snapshots_dir, raising=False)
    monkeypatch.setattr(george_v2, "DECISIONS_LATEST", latest_file, raising=False)

    # Verzeichnisse anlegen
    decisions_dir.mkdir(parents=True, exist_ok=True)
    history_dir.mkdir(parents=True, exist_ok=True)
    snapshots_dir.mkdir(parents=True, exist_ok=True)

    # Beispiel-Decision erzeugen
    decision = george_v2.Decision(
        id="test-dec-001",
        timestamp=george_v2.now_iso(),
        source_event_id=None,
        agent="content",
        action="create_test_content",
        intent="test",
        confidence=0.95,
        status="success",
        error_message=None,
        guardian_flag=None,
        follow_up=None,
        result_summary="Test decision for persistence layer",
    )

    # Aktion
    george_v2.save_decision(decision)

    today = date.today().isoformat()

    # 1) History: DATE.jsonl
    history_file = history_dir / f"{today}.jsonl"
    assert history_file.exists(), "History-File für heute sollte existieren"

    lines = history_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) >= 1, "History-File sollte mindestens einen Eintrag enthalten"

    last_entry = json.loads(lines[-1])
    assert last_entry["id"] == "test-dec-001"
    assert last_entry["agent"] == "content"

    # 2) latest.json
    assert latest_file.exists(), "latest.json sollte geschrieben worden sein"
    latest = json.loads(latest_file.read_text(encoding="utf-8"))
    assert latest["id"] == "test-dec-001"
    assert latest["status"] == "success"

    # 3) Snapshot DATE.json
    snapshot_file = snapshots_dir / f"{today}.json"
    assert snapshot_file.exists(), "Snapshot-File für heute sollte existieren"

    snapshot = json.loads(snapshot_file.read_text(encoding="utf-8"))
    assert snapshot["date"] == today
    assert snapshot["total_decisions"] >= 1
    assert snapshot["successful"] >= 1
    assert "by_agent" in snapshot
    assert "content" in snapshot["by_agent"]
    assert snapshot["by_agent"]["content"]["total"] >= 1


# ---------------------------------------------------------------------------
# Tests: Escalation- & Self-Healing-Regeln (nur Struktur, kein Voll-Sim)
# ---------------------------------------------------------------------------

def test_autonomy_escalation_rules_present_and_sane() -> None:
    """autonomy.json muss sinnvolle escalation_rules & self_healing enthalten."""
    cfg = george_v2.load_autonomy_config()
    rules = cfg.get("escalation_rules", {})
    self_heal = cfg.get("self_healing", {})

    # Es sollten mindestens diese Keys vorhanden sein
    for key in ["on_agent_failure", "on_security_violation", "on_health_drop"]:
        assert key in rules, f"Escalation Rule '{key}' fehlt in autonomy.json"

    assert isinstance(self_heal, dict)
    assert "strategy" in self_heal
    assert self_heal.get("strategy") in {"self_heal_first", "guardian_takeover", "mixed"}
    assert "fallback" in self_heal


# ---------------------------------------------------------------------------
# Optional: Orchestrierungs-Happy-Path (wird nur ausgeführt, wenn Funktion existiert)
# ---------------------------------------------------------------------------

def test_orchestrate_function_smoke(monkeypatch, tmp_path) -> None:
    """
    Leichter Smoke-Test für die Orchestrierung:
    - nur ausführen, wenn eine Funktion 'orchestrate' ODER 'orchestrate_latest_event' existiert
    - side effects (Decisions) werden in ein Temp-Verzeichnis umgeleitet
    """
    orchestrate_fn = getattr(george_v2, "orchestrate", None) or getattr(
        george_v2, "orchestrate_latest_event", None
    )
    if orchestrate_fn is None:
        pytest.skip("Keine orchestrate-Funktion in GEORGE V2 gefunden – Smoke-Test übersprungen")

    # Persistenz in Temp umleiten
    decisions_dir = tmp_path / "decisions"
    history_dir = decisions_dir / "history"
    snapshots_dir = decisions_dir / "snapshots"
    latest_file = decisions_dir / "latest.json"

    monkeypatch.setattr(george_v2, "DECISIONS_DIR", decisions_dir, raising=False)
    monkeypatch.setattr(george_v2, "DECISIONS_HISTORY_DIR", history_dir, raising=False)
    monkeypatch.setattr(george_v2, "DECISIONS_SNAPSHOTS_DIR", snapshots_dir, raising=False)
    monkeypatch.setattr(george_v2, "DECISIONS_LATEST", latest_file, raising=False)

    decisions_dir.mkdir(parents=True, exist_ok=True)
    history_dir.mkdir(parents=True, exist_ok=True)
    snapshots_dir.mkdir(parents=True, exist_ok=True)

    # Wichtig: orchestrate im Dry-Run laufen lassen, falls das Flag existiert
    try:
        result = orchestrate_fn(dry_run=True)  # type: ignore[call-arg]
    except TypeError:
        # Falls es kein dry_run-Argument gibt
        result = orchestrate_fn()  # type: ignore[call-arg]

    # Ergebnis ist entweder None (kein Event) oder eine Decision-ähnliche Struktur
    if result is None:
        # Kein Event vorhanden -> das ist ok
        return

    # Wenn eine Decision zurückkommt, minimal validieren
    if isinstance(result, george_v2.Decision):
        dec_dict = result.to_dict()
    else:
        dec_dict = dict(result)

    assert "agent" in dec_dict
    assert "status" in dec_dict
    assert dec_dict["status"] in {"pending", "success", "error", "blocked"}
