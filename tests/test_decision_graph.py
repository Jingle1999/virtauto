import pytest

from virtauto_core.decision_graph import DecisionGraph
from virtauto_core.decision_object import DecisionObject


def build_decision(
    decision_id: str,
    decision_type: str = "production_recovery_v1",
    selected_action: str = "ALLOW",
) -> DecisionObject:
    return DecisionObject(
        decision_id=decision_id,
        decision_type=decision_type,
        timestamp="2026-07-16T14:00:00Z",
        selected_action=selected_action,
        context={
            "runtime_state": {
                "line_id": "BIW-TVL-01",
            }
        },
        governance={
            "audit_required": True,
        },
        evidence=[],
    )


def build_graph() -> DecisionGraph:
    graph = DecisionGraph()

    graph.add_nodes(
        [
            build_decision(
                decision_id="DEC-001",
                decision_type="machine_failure_v1",
                selected_action="BLOCK",
            ),
            build_decision(
                decision_id="DEC-002",
                decision_type="production_recovery_v1",
                selected_action="ALLOW",
            ),
            build_decision(
                decision_id="DEC-003",
                decision_type="quality_issue_v1",
                selected_action="HOLD",
            ),
        ]
    )

    return graph


def test_add_and_retrieve_decision_node():
    graph = DecisionGraph()
    decision = build_decision("DEC-001")

    stored = graph.add_node(decision)

    assert stored == decision
    assert graph.node_count == 1
    assert graph.has_node("DEC-001") is True
    assert graph.get_node("DEC-001") == decision


def test_duplicate_node_is_rejected():
    graph = DecisionGraph()
    decision = build_decision("DEC-001")

    graph.add_node(decision)

    with pytest.raises(
        ValueError,
        match="Decision Object already exists",
    ):
        graph.add_node(decision)


def test_existing_node_can_be_replaced_explicitly():
    graph = DecisionGraph()

    original = build_decision(
        decision_id="DEC-001",
        selected_action="HOLD",
    )
    replacement = build_decision(
        decision_id="DEC-001",
        selected_action="ALLOW",
    )

    graph.add_node(original)
    graph.add_node(
        replacement,
        replace=True,
    )

    assert graph.node_count == 1
    assert graph.require_node(
        "DEC-001"
    ).selected_action == "ALLOW"


def test_add_directed_relationship():
    graph = build_graph()

    relationship = graph.add_edge(
        source_id="DEC-001",
        target_id="DEC-002",
        relationship_type="resolved_by",
        metadata={
            "confidence": 1.0,
            "source": "manual",
        },
    )

    assert graph.edge_count == 1
    assert relationship.source_id == "DEC-001"
    assert relationship.target_id == "DEC-002"
    assert relationship.relationship_type == "resolved_by"
    assert relationship.relationship_id == (
        "DEC-001::resolved_by::DEC-002"
    )

    assert graph.has_edge(
        source_id="DEC-001",
        target_id="DEC-002",
        relationship_type="resolved_by",
    )


def test_relationship_requires_existing_source_node():
    graph = build_graph()

    with pytest.raises(
        KeyError,
        match="Decision Object not found",
    ):
        graph.add_edge(
            source_id="DEC-999",
            target_id="DEC-002",
            relationship_type="resolved_by",
        )


def test_relationship_requires_existing_target_node():
    graph = build_graph()

    with pytest.raises(
        KeyError,
        match="Decision Object not found",
    ):
        graph.add_edge(
            source_id="DEC-001",
            target_id="DEC-999",
            relationship_type="resolved_by",
        )


def test_duplicate_relationship_is_rejected():
    graph = build_graph()

    graph.add_edge(
        source_id="DEC-001",
        target_id="DEC-002",
        relationship_type="resolved_by",
    )

    with pytest.raises(
        ValueError,
        match="Decision relationship already exists",
    ):
        graph.add_edge(
            source_id="DEC-001",
            target_id="DEC-002",
            relationship_type="resolved_by",
        )


def test_self_relationship_is_rejected():
    graph = build_graph()

    with pytest.raises(
        ValueError,
        match=(
            "source_id and target_id must reference "
            "different Decision Objects"
        ),
    ):
        graph.add_edge(
            source_id="DEC-001",
            target_id="DEC-001",
            relationship_type="same_as",
        )


def test_get_outgoing_and_incoming_relationships():
    graph = build_graph()

    graph.add_edge(
        source_id="DEC-001",
        target_id="DEC-002",
        relationship_type="resolved_by",
    )
    graph.add_edge(
        source_id="DEC-003",
        target_id="DEC-002",
        relationship_type="related_to",
    )

    outgoing = graph.get_outgoing_relationships("DEC-001")
    incoming = graph.get_incoming_relationships("DEC-002")

    assert len(outgoing) == 1
    assert outgoing[0].target_id == "DEC-002"

    assert len(incoming) == 2
    assert {
        relationship.source_id
        for relationship in incoming
    } == {
        "DEC-001",
        "DEC-003",
    }


def test_get_neighbors_by_direction():
    graph = build_graph()

    graph.add_edge(
        source_id="DEC-001",
        target_id="DEC-002",
        relationship_type="resolved_by",
    )
    graph.add_edge(
        source_id="DEC-003",
        target_id="DEC-001",
        relationship_type="triggered",
    )

    outgoing = graph.get_neighbors(
        decision_id="DEC-001",
        direction="outgoing",
    )
    incoming = graph.get_neighbors(
        decision_id="DEC-001",
        direction="incoming",
    )
    both = graph.get_neighbors(
        decision_id="DEC-001",
        direction="both",
    )

    assert [
        decision.decision_id
        for decision in outgoing
    ] == ["DEC-002"]

    assert [
        decision.decision_id
        for decision in incoming
    ] == ["DEC-003"]

    assert [
        decision.decision_id
        for decision in both
    ] == [
        "DEC-002",
        "DEC-003",
    ]


def test_get_neighbors_can_filter_relationship_type():
    graph = build_graph()

    graph.add_edge(
        source_id="DEC-001",
        target_id="DEC-002",
        relationship_type="resolved_by",
    )
    graph.add_edge(
        source_id="DEC-001",
        target_id="DEC-003",
        relationship_type="related_to",
    )

    neighbors = graph.get_neighbors(
        decision_id="DEC-001",
        direction="outgoing",
        relationship_type="resolved_by",
    )

    assert [
        decision.decision_id
        for decision in neighbors
    ] == ["DEC-002"]


def test_remove_node_also_removes_connected_relationships():
    graph = build_graph()

    graph.add_edge(
        source_id="DEC-001",
        target_id="DEC-002",
        relationship_type="resolved_by",
    )
    graph.add_edge(
        source_id="DEC-003",
        target_id="DEC-001",
        relationship_type="triggered",
    )

    removed = graph.remove_node("DEC-001")

    assert removed.decision_id == "DEC-001"
    assert graph.node_count == 2
    assert graph.edge_count == 0
    assert graph.has_node("DEC-001") is False


def test_graph_can_be_exported_to_dictionary():
    graph = build_graph()

    graph.add_edge(
        source_id="DEC-001",
        target_id="DEC-002",
        relationship_type="resolved_by",
        metadata={
            "confidence": 1.0,
        },
    )

    result = graph.to_dict()

    assert result["schema_version"] == "decision_graph_v0.1"
    assert result["node_count"] == 3
    assert result["edge_count"] == 1
    assert len(result["nodes"]) == 3
    assert len(result["edges"]) == 1

    assert result["edges"][0]["source_id"] == "DEC-001"
    assert result["edges"][0]["target_id"] == "DEC-002"
    assert result["edges"][0]["relationship_type"] == (
        "resolved_by"
    )


def test_clear_removes_complete_graph():
    graph = build_graph()

    graph.add_edge(
        source_id="DEC-001",
        target_id="DEC-002",
        relationship_type="resolved_by",
    )

    graph.clear()

    assert graph.node_count == 0
    assert graph.edge_count == 0
    assert graph.list_nodes() == []
    assert graph.list_edges() == []
