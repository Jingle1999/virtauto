import pytest

from virtauto_core.decision_object import DecisionObject


def valid_trace():
    return {
        "decision_id": "DEC-2026-000001",
        "contract_id": "production_recovery_v1",
        "timestamp": "2026-07-14T14:00:00Z",
        "decision": "ALLOW",
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
            }
        ],
    }


def test_create_decision_object_from_runtime_artifacts():
    snapshot = {
        "snapshot_id": "SNAP-2026-000001",
        "captured_at": "2026-07-14T14:00:00Z",
    }

    runtime_state = {
        "line_id": "BIW-TVL-01",
        "production_active": True,
    }

    contract = {
        "contract_id": "production_recovery_v1",
        "action": "ALLOW",
        "default_state": "HOLD",
    }

    decision_object = DecisionObject.from_runtime_artifacts(
        trace=valid_trace(),
        snapshot=snapshot,
        runtime_state=runtime_state,
        contract=contract,
    )

    assert decision_object.decision_id == "DEC-2026-000001"
    assert decision_object.decision_type == "production_recovery_v1"
    assert decision_object.selected_action == "ALLOW"
    assert decision_object.snapshot_id == "SNAP-2026-000001"
    assert decision_object.trace_id == "DEC-2026-000001"
    assert decision_object.schema_version == "decision_object_v0.1"

    assert decision_object.context["runtime_state"]["line_id"] == (
        "BIW-TVL-01"
    )
    assert decision_object.governance["audit_required"] is True
    assert len(decision_object.evidence) == 1


def test_decision_object_can_be_serialized_to_dictionary():
    decision_object = DecisionObject.from_runtime_artifacts(
        trace=valid_trace()
    )

    result = decision_object.to_dict()

    assert result["decision_id"] == "DEC-2026-000001"
    assert result["decision_type"] == "production_recovery_v1"
    assert result["selected_action"] == "ALLOW"
    assert result["schema_version"] == "decision_object_v0.1"
    assert isinstance(result["evidence"], list)
    assert isinstance(result["relationships"], list)


def test_decision_object_rejects_unknown_action():
    trace = valid_trace()
    trace["decision"] = "EXECUTE_IMMEDIATELY"

    with pytest.raises(
        ValueError,
        match="selected_action must be one of",
    ):
        DecisionObject.from_runtime_artifacts(trace=trace)


def test_decision_object_rejects_invalid_timestamp():
    trace = valid_trace()
    trace["timestamp"] = "14 July 2026"

    with pytest.raises(
        ValueError,
        match="timestamp must use ISO 8601 format",
    ):
        DecisionObject.from_runtime_artifacts(trace=trace)


def test_decision_object_rejects_missing_decision_id():
    trace = valid_trace()
    trace.pop("decision_id")

    with pytest.raises(
        ValueError,
        match="decision_id must not be empty",
    ):
        DecisionObject.from_runtime_artifacts(trace=trace)


def test_decision_object_is_frozen():
    decision_object = DecisionObject.from_runtime_artifacts(
        trace=valid_trace()
    )

    with pytest.raises(Exception):
        decision_object.selected_action = "BLOCK"
