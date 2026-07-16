from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


ALLOWED_ACTIONS = {"ALLOW", "HOLD", "BLOCK"}


@dataclass(frozen=True, slots=True)
class DecisionObject:
    """
    Immutable representation of one governed decision.

    A DecisionObject is the atomic unit of the Decision Corpus.
    It contains the decision itself together with its context,
    evidence, governance information and references to the
    runtime artifacts from which it was created.

    The object does not evaluate or execute decisions.
    """

    decision_id: str
    decision_type: str
    timestamp: str
    selected_action: str

    context: dict[str, Any] = field(default_factory=dict)
    governance: dict[str, Any] = field(default_factory=dict)
    evidence: list[Any] = field(default_factory=list)
    alternatives: list[Any] = field(default_factory=list)
    expected_outcome: dict[str, Any] = field(default_factory=dict)
    actual_outcome: dict[str, Any] = field(default_factory=dict)
    relationships: list[dict[str, Any]] = field(default_factory=list)

    trace_id: str | None = None
    snapshot_id: str | None = None
    contract: dict[str, Any] | None = None

    schema_version: str = "decision_object_v0.1"

    def __post_init__(self) -> None:
        """
        Validate the Decision Object immediately after creation.
        """

        self._validate_required_string(
            field_name="decision_id",
            value=self.decision_id,
        )
        self._validate_required_string(
            field_name="decision_type",
            value=self.decision_type,
        )
        self._validate_required_string(
            field_name="timestamp",
            value=self.timestamp,
        )
        self._validate_required_string(
            field_name="selected_action",
            value=self.selected_action,
        )

        self._validate_timestamp()
        self._validate_action()

        if not isinstance(self.context, dict):
            raise TypeError("context must be a dictionary")

        if not isinstance(self.governance, dict):
            raise TypeError("governance must be a dictionary")

        if not isinstance(self.evidence, list):
            raise TypeError("evidence must be a list")

        if not isinstance(self.alternatives, list):
            raise TypeError("alternatives must be a list")

        if not isinstance(self.expected_outcome, dict):
            raise TypeError("expected_outcome must be a dictionary")

        if not isinstance(self.actual_outcome, dict):
            raise TypeError("actual_outcome must be a dictionary")

        if not isinstance(self.relationships, list):
            raise TypeError("relationships must be a list")

        if self.contract is not None and not isinstance(self.contract, dict):
            raise TypeError("contract must be a dictionary or None")

    @staticmethod
    def _validate_required_string(
        field_name: str,
        value: str,
    ) -> None:
        if not isinstance(value, str):
            raise TypeError(f"{field_name} must be a string")

        if not value.strip():
            raise ValueError(f"{field_name} must not be empty")

    def _validate_action(self) -> None:
        if self.selected_action not in ALLOWED_ACTIONS:
            allowed = ", ".join(sorted(ALLOWED_ACTIONS))
            raise ValueError(
                f"selected_action must be one of: {allowed}"
            )

    def _validate_timestamp(self) -> None:
        normalized_timestamp = self.timestamp.replace("Z", "+00:00")

        try:
            datetime.fromisoformat(normalized_timestamp)
        except ValueError as exc:
            raise ValueError(
                "timestamp must use ISO 8601 format"
            ) from exc

    @classmethod
    def from_runtime_artifacts(
        cls,
        trace: dict[str, Any],
        snapshot: dict[str, Any] | None = None,
        runtime_state: dict[str, Any] | None = None,
        contract: dict[str, Any] | None = None,
    ) -> DecisionObject:
        """
        Create a DecisionObject from existing runtime artifacts.

        No decision evaluation occurs here. The method only
        transforms already existing runtime information.
        """

        if not isinstance(trace, dict):
            raise TypeError("trace must be a dictionary")

        snapshot_id = None

        if snapshot is not None:
            if not isinstance(snapshot, dict):
                raise TypeError("snapshot must be a dictionary")

            snapshot_id = snapshot.get("snapshot_id")

        return cls(
            decision_id=trace.get("decision_id", ""),
            decision_type=trace.get("contract_id", ""),
            timestamp=trace.get("timestamp", ""),
            selected_action=trace.get("decision", ""),
            context={
                "runtime_state": deepcopy(runtime_state),
                "snapshot": deepcopy(snapshot),
            },
            governance=deepcopy(trace.get("governance", {})),
            evidence=deepcopy(trace.get("evidence", [])),
            alternatives=deepcopy(trace.get("alternatives", [])),
            expected_outcome=deepcopy(
                trace.get("expected_outcome", {})
            ),
            actual_outcome=deepcopy(
                trace.get("actual_outcome", {})
            ),
            relationships=deepcopy(
                trace.get("relationships", [])
            ),
            trace_id=trace.get(
                "trace_id",
                trace.get("decision_id"),
            ),
            snapshot_id=snapshot_id,
            contract=deepcopy(contract),
        )

    def to_dict(self) -> dict[str, Any]:
        """
        Return a JSON-serializable representation.
        """

        return {
            "decision_id": self.decision_id,
            "decision_type": self.decision_type,
            "timestamp": self.timestamp,
            "context": deepcopy(self.context),
            "governance": deepcopy(self.governance),
            "evidence": deepcopy(self.evidence),
            "alternatives": deepcopy(self.alternatives),
            "selected_action": self.selected_action,
            "expected_outcome": deepcopy(self.expected_outcome),
            "actual_outcome": deepcopy(self.actual_outcome),
            "relationships": deepcopy(self.relationships),
            "trace_id": self.trace_id,
            "snapshot_id": self.snapshot_id,
            "contract": deepcopy(self.contract),
            "schema_version": self.schema_version,
        }
