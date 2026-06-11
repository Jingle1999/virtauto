import json
from pathlib import Path


class DecisionKernel:
    def __init__(
        self,
        runtime_state_path,
        contract_path,
        trace_path="decision_traces/george_decision_trace.jsonl",
    ):
        self.runtime_state_path = Path(runtime_state_path)
        self.contract_path = Path(contract_path)
        self.trace_path = Path(trace_path)

    def load_runtime_state(self):
        with self.runtime_state_path.open() as f:
            return json.load(f)

    def load_contract(self):
        with self.contract_path.open() as f:
            return self._load_simple_yaml(f.read())

    def _load_simple_yaml(self, content):
        result = {}

        for line in content.splitlines():
            line = line.strip()

            if not line or line.startswith("#"):
                continue

            if ":" in line and not line.startswith("-"):
                key, value = line.split(":", 1)
                key = key.strip()
                value = value.strip()

                if value.lower() == "true":
                    value = True
                elif value.lower() == "false":
                    value = False
                elif value.replace(".", "", 1).isdigit():
                    value = float(value) if "." in value else int(value)

                result[key] = value

        return result

    def evaluate_contract(self, runtime_state, contract):
        contract_id = contract.get("contract_id", "unknown_contract")

        production_active = runtime_state.get("production_active")
        energy_kw = runtime_state.get("energy_kw", 0)
        minute_in_shift = runtime_state.get("minute_in_shift", 999)
        jph_actual = runtime_state.get("jph_actual", 0)
        buffer_units = runtime_state.get("buffer_units", 0)

        if contract_id == "shift_change_v1":
            condition_matched = minute_in_shift <= 5

            if condition_matched:
                decision = contract.get("action", "HOLD")
                reason = contract.get(
                    "reason",
                    "Shift transition in progress",
                )
            else:
                decision = "ALLOW"
                reason = "No shift transition condition matched"

        elif contract_id == "production_recovery_v1":
            condition_matched = (
                production_active is True
                and jph_actual > contract.get("jph_actual_gt", 30)
                and buffer_units > contract.get("buffer_units_gt", 5)
            )

            if condition_matched:
                decision = contract.get("action", "ALLOW")
                reason = contract.get(
                    "reason",
                    "Production recovered",
                )
            else:
                decision = "HOLD"
                reason = "Production recovery conditions not met"

        else:
            energy_threshold = contract.get("energy_kw_gt", 10)

            condition_matched = (
                production_active is False
                and energy_kw > energy_threshold
            )

            if condition_matched:
                decision = contract.get("action", "BLOCK")
                reason = contract.get(
                    "reason",
                    "Idle consumption detected",
                )
            else:
                decision = "ALLOW"
                reason = "No contract condition matched"

        evidence = self.create_evidence(
            runtime_state=runtime_state,
            contract=contract,
            condition_matched=condition_matched,
            decision=decision,
            reason=reason,
        )

        trace = self.create_trace(
            runtime_state=runtime_state,
            contract=contract,
            evidence=evidence,
            decision=decision,
            reason=reason,
        )

        return trace

    def create_evidence(
        self,
        runtime_state,
        contract,
        condition_matched,
        decision,
        reason,
    ):
        return {
            "contract_id": contract.get("contract_id", "unknown_contract"),
            "source": "GEORGE Decision Kernel",
            "condition_matched": condition_matched,
            "decision": decision,
            "reason": reason,
            "facts": {
                "production_active": runtime_state.get("production_active"),
                "energy_kw": runtime_state.get("energy_kw"),
                "shift": runtime_state.get("shift"),
                "minute_in_shift": runtime_state.get("minute_in_shift"),
                "variant": runtime_state.get("variant"),
                "jph_actual": runtime_state.get("jph_actual"),
                "buffer_units": runtime_state.get("buffer_units"),
                "quality_state": runtime_state.get("quality_state"),
                "machine_state": runtime_state.get("machine_state"),
                "active_anomalies": runtime_state.get("active_anomalies", []),
            },
        }

    def create_trace(
        self,
        runtime_state,
        contract,
        evidence,
        decision,
        reason,
    ):
        return {
            "decision_id": f"DEC-{runtime_state.get('timestamp')}",
            "contract_id": contract.get("contract_id", "unknown_contract"),
            "runtime_state_id": runtime_state.get(
                "schema_id",
                "runtime_state_v1",
            ),
            "timestamp": runtime_state.get("timestamp"),
            "decision": decision,
            "runtime_state": decision,
            "reason": reason,
            "evidence": evidence,
            "governance": {
                "human_approval_required": True,
                "autonomous_action_allowed": False,
                "audit_required": True,
                "default_state": contract.get("default_state", "HOLD"),
            },
        }

    def write_trace(self, trace):
        self.trace_path.parent.mkdir(parents=True, exist_ok=True)

        with self.trace_path.open("a") as f:
            f.write(json.dumps(trace) + "\n")

    def run(self):
        runtime_state = self.load_runtime_state()
        contract = self.load_contract()

        trace = self.evaluate_contract(
            runtime_state=runtime_state,
            contract=contract,
        )

        self.write_trace(trace)
        return trace
