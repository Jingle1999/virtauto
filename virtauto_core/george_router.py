import json
from pathlib import Path


class GeorgeRouter:

    def __init__(self):
        self.trace_path = Path(
            "decision_traces/george_trace.jsonl"
        )

    def route(self, decisions: list):

        decision_priority = {
            "BLOCK": 3,
            "HOLD": 2,
            "ALLOW": 1,
        }

        contract_priority = {
            "safety_violation_v1": 100,
            "machine_failure_v1": 90,
            "quality_issue_v1": 80,
            "shift_change_v1": 70,
            "variant_change_v1": 60,
            "material_shortage_v1": 50,
            "production_recovery_v1": 40,
            "idle_loss_v1": 30,
        }

        final = sorted(
            decisions,
            key=lambda x: (
                decision_priority.get(x.get("decision"), 0),
                contract_priority.get(x.get("contract_id"), 0),
            ),
            reverse=True,
        )[0]

        george_decision = {
            "decision_id": final.get("decision_id"),
            "contract_id": final.get("contract_id"),
            "runtime_state": final.get("decision"),
            "decision": final.get("decision"),
            "source_agent": final.get("agent"),
            "reason": final.get("reason"),
            "timestamp": final.get("timestamp"),
            "evidence": final.get("evidence"),
            "prioritization": {
                "decision_priority": decision_priority.get(
                    final.get("decision"),
                    0,
                ),
                "contract_priority": contract_priority.get(
                    final.get("contract_id"),
                    0,
                ),
                "rule": "Decision severity first, domain priority second",
            },
        }

        self.trace_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with self.trace_path.open("a") as f:
            f.write(
                json.dumps(george_decision) + "\n"
            )

        print(
            f"GEORGE FINAL -> {george_decision}"
        )

        return george_decision