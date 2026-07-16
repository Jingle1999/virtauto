from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Any, Callable, Iterable

from virtauto_core.decision_graph import (
    DecisionGraph,
    DecisionRelationship,
)
from virtauto_core.decision_object import DecisionObject


ValueExtractor = Callable[[DecisionObject], Any]


@dataclass(frozen=True, slots=True)
class RelationshipRule:
    """
    Deterministic rule for deriving a relationship.

    A rule compares one normalized attribute of two Decision Objects.
    If both values exist and are equal, the configured relationship
    type is created.

    The rule does not execute decisions, infer causality or change
    Decision Objects.
    """

    name: str
    relationship_type: str
    extractor: ValueExtractor

    def __post_init__(self) -> None:
        self._validate_required_string("name", self.name)
        self._validate_required_string(
            "relationship_type",
            self.relationship_type,
        )

        if not callable(self.extractor):
            raise TypeError("extractor must be callable")

    @staticmethod
    def _validate_required_string(
        field_name: str,
        value: str,
    ) -> None:
        if not isinstance(value, str):
            raise TypeError(f"{field_name} must be a string")

        if not value.strip():
            raise ValueError(f"{field_name} must not be empty")


class RelationshipBuilder:
    """
    Derives explicit relationships between Decision Objects.

    Version 0.1 uses deterministic equality rules only. It compares
    governed decision attributes such as decision type, contract,
    production line, station, machine and supplier.

    The builder deliberately performs no:

    - causal inference,
    - semantic similarity calculation,
    - embedding generation,
    - LLM-based classification,
    - graph persistence,
    - decision evaluation.

    Those responsibilities belong to later components.

    Example:
        DEC-001 --same_line_as--> DEC-002
        DEC-001 --same_machine_as--> DEC-004
        DEC-002 --same_contract_as--> DEC-008
    """

    BUILDER_VERSION = "relationship_builder_v0.1"

    def __init__(
        self,
        rules: Iterable[RelationshipRule] | None = None,
    ) -> None:
        """
        Initialize the builder.

        Args:
            rules:
                Optional custom relationship rules. If omitted, the
                default deterministic industrial rules are used.
        """

        if rules is None:
            self._rules = tuple(self._default_rules())
        else:
            self._rules = tuple(rules)

        if not self._rules:
            raise ValueError(
                "RelationshipBuilder requires at least one rule"
            )

        for rule in self._rules:
            if not isinstance(rule, RelationshipRule):
                raise TypeError(
                    "rules must contain RelationshipRule instances"
                )

    @property
    def rules(self) -> tuple[RelationshipRule, ...]:
        """
        Return the configured relationship rules.
        """

        return self._rules

    def build(
        self,
        graph: DecisionGraph,
    ) -> DecisionGraph:
        """
        Derive and add relationships for all nodes in a graph.

        Each unordered pair of Decision Objects is evaluated once.
        Existing relationships are preserved and are not duplicated.

        The supplied graph is updated in place and returned for
        convenient pipeline composition.

        Args:
            graph:
                DecisionGraph whose nodes should be compared.

        Returns:
            The updated DecisionGraph.

        Raises:
            TypeError:
                If graph is not a DecisionGraph.
        """

        if not isinstance(graph, DecisionGraph):
            raise TypeError("graph must be a DecisionGraph")

        decisions = graph.list_nodes()

        for source, target in combinations(decisions, 2):
            relationships = self.infer_relationships(
                source=source,
                target=target,
            )

            for relationship in relationships:
                if graph.has_edge(
                    source_id=relationship.source_id,
                    target_id=relationship.target_id,
                    relationship_type=(
                        relationship.relationship_type
                    ),
                ):
                    continue

                graph.add_edge(
                    source_id=relationship.source_id,
                    target_id=relationship.target_id,
                    relationship_type=(
                        relationship.relationship_type
                    ),
                    metadata=relationship.metadata,
                )

        return graph

    def infer_relationships(
        self,
        source: DecisionObject,
        target: DecisionObject,
    ) -> list[DecisionRelationship]:
        """
        Derive deterministic relationships between two decisions.

        Symmetric equality relationships are stored in one canonical
        direction. The Decision Object with the lexicographically
        smaller identifier becomes the source node. This prevents
        duplicate pairs such as:

            DEC-001 --same_line_as--> DEC-002

        and:

            DEC-002 --same_line_as--> DEC-001

        Args:
            source:
                First Decision Object.

            target:
                Second Decision Object.

        Returns:
            Derived DecisionRelationship instances.
        """

        self._validate_decision("source", source)
        self._validate_decision("target", target)

        if source.decision_id == target.decision_id:
            raise ValueError(
                "source and target must be different Decision Objects"
            )

        canonical_source, canonical_target = (
            self._canonical_order(source, target)
        )

        relationships: list[DecisionRelationship] = []

        for rule in self._rules:
            source_value = self._normalize_value(
                rule.extractor(canonical_source)
            )
            target_value = self._normalize_value(
                rule.extractor(canonical_target)
            )

            if source_value is None or target_value is None:
                continue

            if source_value != target_value:
                continue

            relationships.append(
                DecisionRelationship(
                    source_id=canonical_source.decision_id,
                    target_id=canonical_target.decision_id,
                    relationship_type=rule.relationship_type,
                    metadata={
                        "builder": self.BUILDER_VERSION,
                        "rule": rule.name,
                        "matched_value": source_value,
                        "inference_type": "deterministic_equality",
                    },
                )
            )

        return relationships

    def build_from_decisions(
        self,
        decisions: Iterable[DecisionObject],
    ) -> DecisionGraph:
        """
        Create and populate a graph from Decision Objects.

        This convenience method adds all supplied decisions as nodes
        and subsequently derives their relationships.

        Args:
            decisions:
                Decision Objects to insert into a new graph.

        Returns:
            A populated DecisionGraph.
        """

        graph = DecisionGraph()
        graph.add_nodes(decisions)

        return self.build(graph)

    @staticmethod
    def _canonical_order(
        first: DecisionObject,
        second: DecisionObject,
    ) -> tuple[DecisionObject, DecisionObject]:
        """
        Return two decisions in deterministic identifier order.
        """

        if first.decision_id < second.decision_id:
            return first, second

        return second, first

    @staticmethod
    def _validate_decision(
        field_name: str,
        decision: DecisionObject,
    ) -> None:
        if not isinstance(decision, DecisionObject):
            raise TypeError(
                f"{field_name} must be a DecisionObject"
            )

    @staticmethod
    def _normalize_value(value: Any) -> Any:
        """
        Normalize comparable values.

        Empty strings and empty collections are treated as missing.
        Strings are stripped, while their case is preserved because
        industrial identifiers may be case-sensitive.
        """

        if value is None:
            return None

        if isinstance(value, str):
            normalized = value.strip()
            return normalized or None

        if isinstance(value, (list, tuple, set, dict)):
            if not value:
                return None

        return value

    @classmethod
    def _default_rules(
        cls,
    ) -> list[RelationshipRule]:
        """
        Return the initial deterministic industrial rule set.
        """

        return [
            RelationshipRule(
                name="matching_decision_type",
                relationship_type="same_decision_type_as",
                extractor=lambda decision: decision.decision_type,
            ),
            RelationshipRule(
                name="matching_contract",
                relationship_type="same_contract_as",
                extractor=cls._extract_contract_id,
            ),
            RelationshipRule(
                name="matching_line",
                relationship_type="same_line_as",
                extractor=lambda decision: cls._extract_runtime_value(
                    decision,
                    "line_id",
                    "line",
                    "production_line_id",
                ),
            ),
            RelationshipRule(
                name="matching_station",
                relationship_type="same_station_as",
                extractor=lambda decision: cls._extract_runtime_value(
                    decision,
                    "station_id",
                    "station",
                    "workstation_id",
                ),
            ),
            RelationshipRule(
                name="matching_machine",
                relationship_type="same_machine_as",
                extractor=lambda decision: cls._extract_runtime_value(
                    decision,
                    "machine_id",
                    "machine",
                    "equipment_id",
                    "asset_id",
                ),
            ),
            RelationshipRule(
                name="matching_supplier",
                relationship_type="same_supplier_as",
                extractor=lambda decision: cls._extract_runtime_value(
                    decision,
                    "supplier_id",
                    "supplier",
                    "vendor_id",
                ),
            ),
        ]

    @staticmethod
    def _extract_contract_id(
        decision: DecisionObject,
    ) -> Any:
        """
        Extract an explicit contract identifier.

        The Decision Object's decision_type is not used as a fallback.
        This keeps same_contract_as semantically separate from
        same_decision_type_as.
        """

        contract = decision.contract

        if not isinstance(contract, dict):
            return None

        for key in (
            "contract_id",
            "id",
            "name",
        ):
            value = contract.get(key)

            if value is not None:
                return value

        return None

    @staticmethod
    def _extract_runtime_value(
        decision: DecisionObject,
        *candidate_keys: str,
    ) -> Any:
        """
        Extract an operational attribute from a Decision Object.

        Runtime values are searched in this order:

        1. context.runtime_state
        2. context.snapshot
        3. context itself
        4. evidence facts

        This allows the builder to work with the current DecisionObject
        structure while remaining tolerant of slightly different
        runtime representations.
        """

        context = decision.context

        if not isinstance(context, dict):
            return None

        runtime_state = context.get("runtime_state")

        value = RelationshipBuilder._find_first_value(
            container=runtime_state,
            candidate_keys=candidate_keys,
        )

        if value is not None:
            return value

        snapshot = context.get("snapshot")

        value = RelationshipBuilder._find_first_value(
            container=snapshot,
            candidate_keys=candidate_keys,
        )

        if value is not None:
            return value

        value = RelationshipBuilder._find_first_value(
            container=context,
            candidate_keys=candidate_keys,
        )

        if value is not None:
            return value

        return RelationshipBuilder._extract_from_evidence(
            evidence=decision.evidence,
            candidate_keys=candidate_keys,
        )

    @staticmethod
    def _find_first_value(
        container: Any,
        candidate_keys: tuple[str, ...],
    ) -> Any:
        """
        Return the first matching value from a dictionary.
        """

        if not isinstance(container, dict):
            return None

        for key in candidate_keys:
            if key in container:
                return container[key]

        return None

    @staticmethod
    def _extract_from_evidence(
        evidence: list[Any],
        candidate_keys: tuple[str, ...],
    ) -> Any:
        """
        Search evidence entries for a matching runtime fact.

        Supported evidence shapes include:

            {
                "name": "machine_id",
                "value": "PRESS-01"
            }

        and:

            {
                "machine_id": "PRESS-01"
            }
        """

        if not isinstance(evidence, list):
            return None

        for item in evidence:
            if not isinstance(item, dict):
                continue

            direct_value = RelationshipBuilder._find_first_value(
                container=item,
                candidate_keys=candidate_keys,
            )

            if direct_value is not None:
                return direct_value

            fact_name = item.get("name")

            if fact_name in candidate_keys:
                return item.get("value")

        return None
