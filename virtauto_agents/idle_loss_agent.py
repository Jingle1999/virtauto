import json
from pathlib import Path

from virtauto_core.base_agent import BaseAgent

DATA_PATH = Path("virtauto_data/synthetic/biw_tvl_week.json")
TRACE_PATH = Path("decision_traces/idle_loss_trace.jsonl")
IDLE_THRESHOLD_KW = 10.0


with DATA_PATH.open() as f:
    data = json.load(f)

events = data["ticks"]


class IdleLossAgent(BaseAgent):

    def __init__(self):
        self.agent_id = "idle_loss"

    def has_idle_loss(self, event):
        return any(
            anomaly["type"] == "idle_loss"
            for anomaly in event["active_anomalies"]
        )

    def evaluate(self, event):
        idle_loss_detected = self.has_idle_loss(event)

        if (
            event["production_active"] is False
            and idle_loss_detected
            and event["energy_kw"] >= IDLE_THRESHOLD_KW
        ):
            return {
                "decision_id": f"IDL-{event['timestamp']}",
                "timestamp": event["timestamp"],
                "line_id": data["meta"]["line_id"],
                "plant_id": data["meta"]["plant_id"],
                "agent": self.agent_id,
                "runtime_state": "BLOCK",
                "decision": "BLOCK",
                "reason": "Idle consumption detected",
                "evidence": {
                    "production_active": event["production_active"],
                    "idle_loss_detected": idle_loss_detected,
                    "energy_kw": event["energy_kw"],
                    "threshold_kw": IDLE_THRESHOLD_KW,
                    "shift": event["shift_label"],
                    "minute_in_shift": event["minute_in_shift"],
                    "jph_actual": event["jph_actual"],
                    "buffer_units": event["buffer_units"],
                    "active_anomalies": event["active_anomalies"],
                },
            }

        return None


agent = IdleLossAgent()

TRACE_PATH.parent.mkdir(parents=True, exist_ok=True)

with TRACE_PATH.open("w") as f:
    for event in events:
        decision = agent.evaluate(event)

        if decision is not None:
            f.write(json.dumps(decision) + "\n")
            print(decision)