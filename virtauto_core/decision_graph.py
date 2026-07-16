from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Iterable

from virtauto_core.decision_object import DecisionObject


@dataclass(frozen=True, slots=True)
class DecisionRelationship:
    """
    Immutable directed relationship between two Decision Objects.

    A relationship connects a source Decision Object to a target
    Decision Object through an explicit relationship type.

    Examples:
        DEC-001 --resolved_by--> DEC-002
        DEC-003 --same_station_as--> DEC-004
        DEC-005 --triggered_by--> DEC-006
    """

    source_id: str
    target_id: str
    relationship_type: str
    metadata: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        self._validate_required_string("source_id", self.source_id)
        self._validate_required_string("target_id", self.target_id)
        self._validate_required_string(
            "relationship_type",
            self.relationship_type,
        )

        if self.source_id == self.target_id:
            raise ValueError(
                "source_id and target_id must reference "
                "different Decision Objects"
            )

        if self.metadata is not None and not isinstance(
            self.metadata,
            dict,
        ):
            raise TypeError("metadata must be a dictionary or None")

    @staticmethod
    def _validate_required_string(
        field_name: str,
        value: str,
    ) -> None:
        if not isinstance(value, str):
            raise TypeError(f"{field_name} must be a string")

        if not value.strip():
            raise ValueError(f"{field_name} must not be empty")

    @property
    def relationship_id(self) -> str:
        """
        Return a deterministic identifier for the relationship.
        """

        return (
            f"{self.source_id}"
            f"::{self.relationship_type}"
            f"::{self.target_id}"
        )

    def to_dict(self) -> dict[str, Any]:
        """
        Return a JSON-serializable representation.
        """

        return {
            "relationship_id": self.relationship_id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relationship_type": self.relationship_type,
            "metadata": deepcopy(self.metadata or {}),
        }


class DecisionGraph:
    """
    In-memory directed graph of governed industrial decisions.

    Decision Objects are stored as graph nodes. Explicit
    DecisionRelationship instances form directed graph edges.

    This class intentionally contains no automatic relationship
    discovery, database integration, embedding generation or
    decision evaluation. Those responsibilities belong to later
    components such as a RelationshipBuilder or graph repository.
    """

    SCHEMA_VERSION = "decision_graph_v0.1"

    def __init__(self) -> None:
        self._nodes: dict[str, DecisionObject] = {}
        self._edges: dict[str, DecisionRelationship] = {}

    @property
    def node_count(self) -> int:
        """
        Return the number of Decision Objects in the graph.
        """

        return len(self._nodes)

    @property
    def edge_count(self) -> int:
        """
        Return the number of relationships in the graph.
        """

        return len(self._edges)

    def add_node(
        self,
        decision: DecisionObject,
        *,
        replace: bool = False,
    ) -> DecisionObject:
        """
        Add a Decision Object as a graph node.

        Args:
            decision:
                Decision Object to add.

            replace:
                Replace an existing node with the same decision ID.
                The default is False to prevent accidental mutation
                of the graph's decision history.

        Returns:
            The stored Decision Object.

        Raises:
            TypeError:
                If decision is not a DecisionObject.

            ValueError:
                If the decision already exists and replace is False.
        """

        if not isinstance(decision, DecisionObject):
            raise TypeError("decision must be a DecisionObject")

        if decision.decision_id in self._nodes and not replace:
            raise ValueError(
                f"Decision Object already exists: "
                f"{decision.decision_id}"
            )

        self._nodes[decision.decision_id] = decision

        return decision

    def add_nodes(
        self,
        decisions: Iterable[DecisionObject],
        *,
        replace: bool = False,
    ) -> None:
        """
        Add multiple Decision Objects to the graph.
        """

        for decision in decisions:
            self.add_node(
                decision,
                replace=replace,
            )

    def get_node(
        self,
        decision_id: str,
    ) -> DecisionObject | None:
        """
        Return a Decision Object by its identifier.
        """

        self._validate_identifier(
            field_name="decision_id",
            value=decision_id,
        )

        return self._nodes.get(decision_id)

    def require_node(
        self,
        decision_id: str,
    ) -> DecisionObject:
        """
        Return a Decision Object or raise KeyError if it is missing.
        """

        decision = self.get_node(decision_id)

        if decision is None:
            raise KeyError(
                f"Decision Object not found: {decision_id}"
            )

        return decision

    def has_node(
        self,
        decision_id: str,
    ) -> bool:
        """
        Return whether the graph contains a Decision Object.
        """

        self._validate_identifier(
            field_name="decision_id",
            value=decision_id,
        )

        return decision_id in self._nodes

    def remove_node(
        self,
        decision_id: str,
    ) -> DecisionObject:
        """
        Remove a Decision Object and all connected relationships.

        Returns:
            The removed Decision Object.

        Raises:
            KeyError:
                If the Decision Object does not exist.
        """

        decision = self.require_node(decision_id)

        relationship_ids = [
            relationship_id
            for relationship_id, relationship in self._edges.items()
            if relationship.source_id == decision_id
            or relationship.target_id == decision_id
        ]

        for relationship_id in relationship_ids:
            del self._edges[relationship_id]

        del self._nodes[decision_id]

        return decision

    def add_edge(
        self,
        source_id: str,
        target_id: str,
        relationship_type: str,
        metadata: dict[str, Any] | None = None,
    ) -> DecisionRelationship:
        """
        Add a directed relationship between two existing nodes.

        Both Decision Objects must already exist in the graph.
        Duplicate relationships are rejected.

        Returns:
            The newly stored DecisionRelationship.
        """

        self.require_node(source_id)
        self.require_node(target_id)

        relationship = DecisionRelationship(
            source_id=source_id,
            target_id=target_id,
            relationship_type=relationship_type,
            metadata=deepcopy(metadata),
        )

        if relationship.relationship_id in self._edges:
            raise ValueError(
                "Decision relationship already exists: "
                f"{relationship.relationship_id}"
            )

        self._edges[relationship.relationship_id] = relationship

        return relationship

    def get_edge(
        self,
        relationship_id: str,
    ) -> DecisionRelationship | None:
        """
        Return a relationship by its deterministic identifier.
        """

        self._validate_identifier(
            field_name="relationship_id",
            value=relationship_id,
        )

        return self._edges.get(relationship_id)

    def has_edge(
        self,
        source_id: str,
        target_id: str,
        relationship_type: str,
    ) -> bool:
        """
        Return whether a specific directed relationship exists.
        """

        relationship_id = self._build_relationship_id(
            source_id=source_id,
            target_id=target_id,
            relationship_type=relationship_type,
        )

        return relationship_id in self._edges

    def remove_edge(
        self,
        source_id: str,
        target_id: str,
        relationship_type: str,
    ) -> DecisionRelationship:
        """
        Remove and return a directed relationship.

        Raises:
            KeyError:
                If the relationship does not exist.
        """

        relationship_id = self._build_relationship_id(
            source_id=source_id,
            target_id=target_id,
            relationship_type=relationship_type,
        )

        relationship = self._edges.get(relationship_id)

        if relationship is None:
            raise KeyError(
                "Decision relationship not found: "
                f"{relationship_id}"
            )

        del self._edges[relationship_id]

        return relationship

    def get_outgoing_relationships(
        self,
        decision_id: str,
        relationship_type: str | None = None,
    ) -> list[DecisionRelationship]:
        """
        Return relationships originating from a Decision Object.
        """

        self.require_node(decision_id)

        return [
            relationship
            for relationship in self._edges.values()
            if relationship.source_id == decision_id
            and (
                relationship_type is None
                or relationship.relationship_type
                == relationship_type
            )
        ]

    def get_incoming_relationships(
        self,
        decision_id: str,
        relationship_type: str | None = None,
    ) -> list[DecisionRelationship]:
        """
        Return relationships pointing to a Decision Object.
        """

        self.require_node(decision_id)

        return [
            relationship
            for relationship in self._edges.values()
            if relationship.target_id == decision_id
            and (
                relationship_type is None
                or relationship.relationship_type
                == relationship_type
            )
        ]

    def get_neighbors(
        self,
        decision_id: str,
        *,
        direction: str = "both",
        relationship_type: str | None = None,
    ) -> list[DecisionObject]:
        """
        Return directly connected Decision Objects.

        Args:
            decision_id:
                Identifier of the reference Decision Object.

            direction:
                "outgoing", "incoming" or "both".

            relationship_type:
                Optional relationship-type filter.

        Returns:
            Connected Decision Objects without duplicates.
        """

        self.require_node(decision_id)

        allowed_directions = {
            "incoming",
            "outgoing",
            "both",
        }

        if direction not in allowed_directions:
            raise ValueError(
                "direction must be one of: "
                "both, incoming, outgoing"
            )

        neighbor_ids: set[str] = set()

        if direction in {"outgoing", "both"}:
            outgoing = self.get_outgoing_relationships(
                decision_id=decision_id,
                relationship_type=relationship_type,
            )

            neighbor_ids.update(
                relationship.target_id
                for relationship in outgoing
            )

        if direction in {"incoming", "both"}:
            incoming = self.get_incoming_relationships(
                decision_id=decision_id,
                relationship_type=relationship_type,
            )

            neighbor_ids.update(
                relationship.source_id
                for relationship in incoming
            )

        return [
            self._nodes[neighbor_id]
            for neighbor_id in sorted(neighbor_ids)
        ]

    def list_nodes(self) -> list[DecisionObject]:
        """
        Return all Decision Objects ordered by decision ID.
        """

        return [
            self._nodes[decision_id]
            for decision_id in sorted(self._nodes)
        ]

    def list_edges(self) -> list[DecisionRelationship]:
        """
        Return all relationships ordered by relationship ID.
        """

        return [
            self._edges[relationship_id]
            for relationship_id in sorted(self._edges)
        ]

    def to_dict(self) -> dict[str, Any]:
        """
        Export the complete graph as JSON-compatible data.
        """

        return {
            "schema_version": self.SCHEMA_VERSION,
            "node_count": self.node_count,
            "edge_count": self.edge_count,
            "nodes": [
                decision.to_dict()
                for decision in self.list_nodes()
            ],
            "edges": [
                relationship.to_dict()
                for relationship in self.list_edges()
            ],
        }

    def clear(self) -> None:
        """
        Remove all nodes and relationships from the graph.
        """

        self._nodes.clear()
        self._edges.clear()

    @staticmethod
    def _validate_identifier(
        field_name: str,
        value: str,
    ) -> None:
        if not isinstance(value, str):
            raise TypeError(f"{field_name} must be a string")

        if not value.strip():
            raise ValueError(f"{field_name} must not be empty")

    @classmethod
    def _build_relationship_id(
        cls,
        source_id: str,
        target_id: str,
        relationship_type: str,
    ) -> str:
        cls._validate_identifier("source_id", source_id)
        cls._validate_identifier("target_id", target_id)
        cls._validate_identifier(
            "relationship_type",
            relationship_type,
        )

        return (
            f"{source_id}"
            f"::{relationship_type}"
            f"::{target_id}"
        )
