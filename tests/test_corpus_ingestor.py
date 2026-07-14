import json

from virtauto_core.corpus_ingestor import CorpusIngestor


def sample_trace():
    return {
        "decision_id": "DEC-2026-000001",
        "contract_id": "production_recovery_v1",
        "timestamp": "2026-07-14T14:00:00Z",
        "decision": "ALLOW",
        "reason": "Production recovery conditions met",
        "governance": {
            "human_approval_required": False,
            "autonomous_action_allowed": True,
            "audit_required": True,
            "default_state": "HOLD",
        },
        "evidence": [
            {
                "type": "runtime_fact",
                "name": "production_active",
                "value": True,
            },
            {
                "type": "runtime_fact",
                "name": "jph_actual",
                "value": 42,
            },
            {
                "type": "runtime_fact",
                "name": "buffer_units",
                "value": 8,
            },
        ],
    }


def sample_runtime_state():
    return {
        "schema_id": "runtime_state_v1",
        "line_id": "BIW-TVL-01",
        "plant_id": "WK-MUC-01",
        "station_id": "DOOR-FL",
        "production_active": True,
        "jph_actual": 42,
        "buffer_units": 8,
        "quality_state": "OK",
        "machine_state": "RUNNING",
    }


def sample_snapshot():
    return {
        "snapshot_id": "SNAP-2026-000001",
        "runtime_state_id": "runtime_state_v1",
        "captured_at": "2026-07-14T14:00:00Z",
    }


def sample_contract():
    return {
        "contract_id": "production_recovery_v1",
        "condition": "production_recovered",
        "action": "ALLOW",
        "default_state": "HOLD",
        "reason": "Production recovered",
    }


def test_build_decision_object(tmp_path):
    ingestor = CorpusIngestor(output_dir=tmp_path)

    decision_object = ingestor.build_decision_object(
        trace=sample_trace(),
        snapshot=sample_snapshot(),
        runtime_state=sample_runtime_state(),
        contract=sample_contract(),
    )

    assert decision_object["decision_id"] == "DEC-2026-000001"
    assert decision_object["decision_type"] == "production_recovery_v1"
    assert decision_object["timestamp"] == "2026-07-14T14:00:00Z"
    assert decision_object["selected_action"] == "ALLOW"
    assert decision_object["schema_version"] == "decision_object_v0.1"

    assert decision_object["context"]["runtime_state"]["line_id"] == "BIW-TVL-01"
    assert decision_object["context"]["snapshot"]["snapshot_id"] == (
        "SNAP-2026-000001"
    )

    assert decision_object["governance"]["audit_required"] is True
    assert len(decision_object["evidence"]) == 3
    assert decision_object["contract"]["contract_id"] == (
        "production_recovery_v1"
    )


def test_write_decision_object(tmp_path):
    ingestor = CorpusIngestor(output_dir=tmp_path)

    decision_object = ingestor.build_decision_object(
        trace=sample_trace(),
        snapshot=sample_snapshot(),
        runtime_state=sample_runtime_state(),
        contract=sample_contract(),
    )

    output_path = ingestor.write_decision_object(decision_object)

    assert output_path.exists()
    assert output_path.name == "DEC-2026-000001.json"

    with output_path.open(encoding="utf-8") as file:
        stored_object = json.load(file)

    assert stored_object == decision_object


def test_ingest_builds_and_writes_decision_object(tmp_path):
    ingestor = CorpusIngestor(output_dir=tmp_path)

    decision_object = ingestor.ingest(
        trace=sample_trace(),
        snapshot=sample_snapshot(),
        runtime_state=sample_runtime_state(),
        contract=sample_contract(),
    )

    output_path = tmp_path / "DEC-2026-000001.json"

    assert output_path.exists()
    assert decision_object["decision_id"] == "DEC-2026-000001"
    assert decision_object["selected_action"] == "ALLOW"

    with output_path.open(encoding="utf-8") as file:
        stored_object = json.load(file)

    assert stored_object["decision_id"] == "DEC-2026-000001"
    assert stored_object["selected_action"] == "ALLOW"
    assert stored_object["schema_version"] == "decision_object_v0.1"
