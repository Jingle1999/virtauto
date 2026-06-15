from virtauto_core.base_agent import BaseAgent


class PeakGuardAgent(BaseAgent):

    async def evaluate(self, event: dict):

        if (
            event["signal_type"] == "energy"
            and event["value"] > event["threshold"]
            and event["production_active"] is False
        ):

            return {
                "agent": self.agent_id,
                "decision": "HOLD",
                "reason": "Energy consumption above threshold while production inactive",
                "event_id": event["event_id"],
                "trace_id": event["trace_id"]
            }

        return {
            "agent": self.agent_id,
            "decision": "ALLOW",
            "reason": "No anomaly detected",
            "event_id": event["event_id"],
            "trace_id": event["trace_id"]
        }