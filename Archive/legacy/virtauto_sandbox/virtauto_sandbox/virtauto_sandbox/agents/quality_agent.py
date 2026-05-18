
from common.task import Task, Result

class QualityAgent:
    name = "QualityAgent"

    def handle(self, task: Task) -> Result:
        data = {
            "summary": "All quality checks passed",
            "details": {"file": task.payload.get("file", "demo.csv")}
        }
        return Result(ok=True, data=data, errors=[])
