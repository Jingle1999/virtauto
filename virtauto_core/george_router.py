import json
from pathlib import Path


class GeorgeRouter:

    def __init__(self):
        self.trace_path = Path(
            "decision_traces/george_trace.jsonl"
        )

    def route(self, decisions: list):

        priority = {
            "BLOCK": 3,
            "HOLD": 2,
            "ALLOW": 1
        }

        final = sorted(
            decisions,
            key=lambda x: priority[x["decision"]],
            reverse=True
        )[0]

        george_decision = {
            "decision_id": final["decision_id"],
            "runtime_state": final["decision"],
            "decision": final["decision"],
            "source_agent": final["agent"],
            "reason": final["reason"],
            "timestamp": final["timestamp"],
            "evidence": final["evidence"]
        }

        self.trace_path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        with self.trace_path.open("a") as f:
            f.write(
                json.dumps(george_decision) + "\n"
            )

        print(
            f"GEORGE FINAL -> {george_decision}"
        )

        return george_decision