import json

from virtauto_core.decision_kernel import DecisionKernel


kernel = DecisionKernel(
    runtime_state_path="virtauto_governance/schemas/runtime_state.json",
    contract_path="virtauto_governance/contracts/machine_failure.yaml",
    trace_path="decision_traces/george_decision_trace.jsonl",
)

trace = kernel.run()

print(json.dumps(trace, indent=2))
