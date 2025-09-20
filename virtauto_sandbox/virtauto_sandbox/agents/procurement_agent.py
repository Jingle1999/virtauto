from common.task import Task, Result

class ProcurementAgent:
    name = "ProcurementAgent"

    def handle(self, task: Task) -> Result:
        part = task.payload.get("part", "unknown")
        qty = task.payload.get("qty", 0)
        data = {
            "summary": "Suppliers confirmed",
            "rationale": f"Confirmed {qty} pcs for part {part}"
        }
        return Result(ok=True, data=data, errors=[])

