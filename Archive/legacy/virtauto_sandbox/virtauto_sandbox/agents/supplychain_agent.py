
from common.task import Task, Result

class SupplyChainAgent:
    name = "SupplyChainAgent"

    def handle(self, task: Task) -> Result:
        demand = task.payload.get("demand", 0)
        horizon = task.payload.get("horizon", "N/A")
        data = {
            "summary": f"Plan feasible for demand {demand} over {horizon}",
            "eta_days": 5
        }
        return Result(ok=True, data=data, errors=[])
