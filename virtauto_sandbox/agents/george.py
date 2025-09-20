
from agents.quality_agent import QualityAgent
from agents.procurement_agent import ProcurementAgent
from agents.supplychain_agent import SupplyChainAgent
from common.task import Task, Result
from consistency.gate import preflight, postflight
from consistency.bridge import precheck as mvp_precheck, postcheck as mvp_postcheck
from logging.audit import audit

class GEORGE:
    def __init__(self):
        self.registry = {
            "quality.analyze_csv": QualityAgent(),
            "procure.suggest_supplier": ProcurementAgent(),
            "sc.plan": SupplyChainAgent(),
        }

    def route(self, task: Task) -> Result:
        ok, errs = preflight(task.__dict__)
        if not ok:
            audit("consistency_pre_fail", {"task_id": task.id, "errors": errs})
            return Result(ok=False, errors=errs)

        mvp_pre = mvp_precheck(task.__dict__)
        if not mvp_pre.get("ok", True):
            audit("mvp_pre_fail", {"task_id": task.id, "errors": mvp_pre.get("errors", [])})
            return Result(ok=False, errors=mvp_pre.get("errors", ["consistency pre failed"]))

        agent = self.registry.get(task.type)
        if not agent:
            return Result(ok=False, errors=[f"no agent for type {task.type}"])
        audit("route", {"task_id": task.id, "to": agent.name})
        res = agent.handle(task)

        ok2, errs2 = postflight({"data": res.data})
        if not ok2:
            audit("consistency_post_fail", {"task_id": task.id, "errors": errs2})
            res.errors.extend(errs2)
            res.ok = False

        mvp_post = mvp_postcheck({"data": res.data})
        if not mvp_post.get("ok", True):
            audit("mvp_post_fail", {"task_id": task.id, "errors": mvp_post.get("errors", [])})
            res.errors.extend(mvp_post.get("errors", []))
            res.ok = False

        return res
