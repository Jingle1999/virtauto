import json
from pathlib import Path
from typing import Any

from virtauto_core.decision_object import DecisionObject


class CorpusIngestor:
    """
    Transforms runtime artifacts into persistent Decision Objects.

    The ingestor does not evaluate, prioritize or execute decisions.
    It only converts existing runtime artifacts into validated
    Decision Objects and stores them in the Decision Corpus.
    """

    def __init__(
        self,
        output_dir: str | Path = "decision_corpus/objects",
    ) -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def build_decision_object(
        self,
        trace: dict[str, Any],
        snapshot: dict[str, Any] | None = None,
        runtime_state: dict[str, Any] | None = None,
        contract: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Build and validate a Decision Object.

        A dictionary is returned to preserve compatibility with the
        current CorpusIngestor interface.
        """

        decision_object = DecisionObject.from_runtime_artifacts(
            trace=trace,
            snapshot=snapshot,
            runtime_state=runtime_state,
            contract=contract,
        )

        return decision_object.to_dict()

    def write_decision_object(
        self,
        decision: dict[str, Any],
    ) -> Path:
        """
        Persist a Decision Object as formatted UTF-8 JSON.
        """

        decision_id = decision.get("decision_id")

        if not isinstance(decision_id, str) or not decision_id.strip():
            raise ValueError(
                "decision must contain a non-empty decision_id"
            )

        filename = self.output_dir / f"{decision_id}.json"

        with filename.open("w", encoding="utf-8") as file:
            json.dump(
                decision,
                file,
                indent=4,
                ensure_ascii=False,
                sort_keys=True,
            )
            file.write("\n")

        return filename

    def ingest(
        self,
        trace: dict[str, Any],
        snapshot: dict[str, Any] | None = None,
        runtime_state: dict[str, Any] | None = None,
        contract: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Build, validate and persist a Decision Object.
        """

        decision = self.build_decision_object(
            trace=trace,
            snapshot=snapshot,
            runtime_state=runtime_state,
            contract=contract,
        )

        self.write_decision_object(decision)

        return decision
