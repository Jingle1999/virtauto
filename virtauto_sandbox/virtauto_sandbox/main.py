
from agents.george import GEORGE
from common.task import Task

def run_demo():
    george = GEORGE()

    demo_tasks = [
        Task(id="t1", type="quality.analyze_csv", payload={"file": "demo.csv"},
             meta={"owner": "Quality", "source": "MES", "kpi": "FPY"}),

        Task(id="t2", type="procure.suggest_supplier",
             payload={"part": "E-Motor", "qty": 10},
             meta={"owner": "Procurement", "source": "SAP", "kpi": "Cost"}),

        Task(id="t3", type="sc.plan",
             payload={"demand": 500, "horizon": "Q1"},
             meta={"owner": "SupplyChain", "source": "ERP", "kpi": "OTD"})
    ]

    for task in demo_tasks:
        res = george.route(task)
        print(f"{task.type.upper()}: {res.__dict__}")

if __name__ == "__main__":
    run_demo()
