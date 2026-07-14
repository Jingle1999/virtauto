import json
from pathlib import Path


class CorpusIngestor:
    """
    Transforms runtime artifacts into Decision Objects.

    The ingestor does NOT evaluate decisions.

    It only converts existing runtime artifacts into
    persistent Decision Objects for the Decision Corpus.
    """

    def __init__(self, output_dir="decision_corpus/objects"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def build_decision_object(
        self,
        trace,
        snapshot=None,
        runtime_state=None,
        contract=None,
    ):

        decision = {
            "decision_id": trace.get("decision_id"),

            "decision_type": trace.get("contract_id"),

            "timestamp": trace.get("timestamp"),

            "context": {
                "runtime_state": runtime_state,
                "snapshot": snapshot,
            },

            "governance": trace.get("governance", {}),

            "evidence": trace.get("evidence", {}),

            "alternatives": [],

            "selected_action": trace.get("decision"),

            "expected_outcome": {},

            "actual_outcome": {},

            "relationships": [],

            "trace_id": trace.get("decision_id"),

            "contract": contract,

            "schema_version": "decision_object_v0.1",
        }

        return decision

    def write_decision_object(self, decision):

        filename = (
            self.output_dir /
            f"{decision['decision_id']}.json"
        )

        with filename.open("w") as f:
            json.dump(decision, f, indent=4)

        return filename

    def ingest(
        self,
        trace,
        snapshot=None,
        runtime_state=None,
        contract=None,
    ):

        decision = self.build_decision_object(
            trace=trace,
            snapshot=snapshot,
            runtime_state=runtime_state,
            contract=contract,
        )

        self.write_decision_object(decision)

        return decision