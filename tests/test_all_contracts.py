import json

from virtauto_core.decision_kernel import DecisionKernel
from virtauto_core.george_router import GeorgeRouter


CONTRACT_PATHS = [
    "virtauto_governance/contracts/idle_loss.yaml",
    "virtauto_governance/contracts/shift_change.yaml",
    "virtauto_governance/contracts/variant_change.yaml",
    "virtauto_governance/contracts/production_recovery.yaml",
    "virtauto_governance/contracts/quality_issue.yaml",
    "virtauto_governance/contracts/machine_failure.yaml",
    "virtauto_governance/contracts/material_shortage.yaml",
    "virtauto_governance/contracts/safety_violation.yaml",
]


def evaluate_all_contracts():
    decisions = []

    for contract_path in CONTRACT_PATHS:
        kernel = DecisionKernel(
            runtime_state_path="virtauto_governance/schemas/runtime_state.json",
            contract_path=contract_path,
            trace_path="decision_traces/george_decision_trace.jsonl",
        )

        trace = kernel.run()
        trace["agent"] = "GEORGE Decision Kernel"
        decisions.append(trace)

    return decisions


decisions = evaluate_all_contracts()

router = GeorgeRouter()
final_decision = router.route(decisions)

summary = {
    "contracts_evaluated": len(decisions),
    "decisions": [
        {
            "contract_id": d.get("contract_id"),
            "decision": d.get("decision"),
            "reason": d.get("reason"),
        }
        for d in decisions
    ],
    "george_final_decision": {
        "decision": final_decision.get("decision"),
        "reason": final_decision.get("reason"),
        "source_contract": final_decision.get("contract_id"),
        "decision_id": final_decision.get("decision_id"),
    },
}

print(json.dumps(summary, indent=2))