import argparse
import json
from pathlib import Path

from virtauto_core.decision_kernel import DecisionKernel
from virtauto_core.snapshot_builder import SnapshotBuilder


DECISION_PRIORITY = {
    "BLOCK": 3,
    "HOLD": 2,
    "ALLOW": 1,
}


def load_json(path):
    with Path(path).open(encoding="utf-8") as f:
        return json.load(f)


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    return str(path)


class DecisionEngine:
    def __init__(
        self,
        runtime_state_path,
        contract_paths,
        latest_path="ops/decisions/latest.json",
        snapshot_path="ops/decisions/snapshots/latest_snapshot.json",
        trace_path="decision_traces/george_decision_trace.jsonl",
    ):
        self.runtime_state_path = Path(runtime_state_path)
        self.contract_paths = [Path(p) for p in contract_paths]
        self.latest_path = latest_path
        self.snapshot_path = snapshot_path
        self.trace_path = trace_path

    def evaluate_contracts(self):
        traces = []

        for contract_path in self.contract_paths:
            kernel = DecisionKernel(
                runtime_state_path=self.runtime_state_path,
                contract_path=contract_path,
                trace_path=self.trace_path,
            )
            trace = kernel.run()
            traces.append(trace)

        return traces

    def route_final_decision(self, traces):
        if not traces:
            return {
                "decision": "HOLD",
                "reason": "No contract traces available",
                "source": "DecisionEngine",
            }

        ordered = sorted(
            traces,
            key=lambda t: DECISION_PRIORITY.get(t.get("decision"), 0),
            reverse=True,
        )

        winning_trace = ordered[0]

        return {
            "decision": winning_trace.get("decision", "HOLD"),
            "reason": winning_trace.get("reason", "No reason provided"),
            "source": "DecisionEngine",
            "winning_contract_id": winning_trace.get("contract_id"),
            "priority_rule": "BLOCK > HOLD > ALLOW",
            "evaluated_contracts": len(traces),
        }

    def run(self):
        runtime_state = load_json(self.runtime_state_path)

        contract_traces = self.evaluate_contracts()
        final_decision = self.route_final_decision(contract_traces)

        latest_output = {
            "final_decision": final_decision,
            "contract_traces": contract_traces,
            "runtime_state_ref": str(self.runtime_state_path),
        }

        latest_written = write_json(self.latest_path, latest_output)

        snapshot = SnapshotBuilder().build(
            runtime_state=runtime_state,
            contract_traces=contract_traces,
            final_decision=final_decision,
        )

        snapshot_written = SnapshotBuilder().write(
            snapshot,
            path=self.snapshot_path,
        )

        return {
            "final_decision": final_decision,
            "latest_written": latest_written,
            "snapshot_written": snapshot_written,
        }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime-state", required=True)
    parser.add_argument("--contracts", nargs="+", required=True)

    args = parser.parse_args()

    engine = DecisionEngine(
        runtime_state_path=args.runtime_state,
        contract_paths=args.contracts,
    )

    result = engine.run()
    print(json.dumps(result, indent=2, ensure_ascii=False))
