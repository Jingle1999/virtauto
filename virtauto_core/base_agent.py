from abc import ABC, abstractmethod
from datetime import datetime


class BaseAgent(ABC):

    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.last_decision = None

    async def observe(self, event: dict):
        return event

    @abstractmethod
    async def evaluate(self, event: dict):
        pass

    async def emit(self, decision: dict):
        self.last_decision = decision
        print(
            f"[{self.agent_id}] "
            f"{decision['decision']} | "
            f"{decision['reason']}"
        )

    async def log_trace(self, decision: dict):
        decision["logged_at"] = datetime.utcnow().isoformat()
        print(f"TRACE -> {decision}")