from __future__ import annotations

from pathlib import Path
from .config import load_config
from .context_builder import ContextBuilder
from .decision import DecisionEngineV1
from .governance import GovernanceGate
from .report import ReportBuilder


def run_pipeline(csv_path: str | Path, config_path: str | Path, output_dir: str | Path) -> dict:
    config = load_config(config_path)
    context = ContextBuilder().build(csv_path, config)
    decision = DecisionEngineV1().evaluate(context, config)
    governance = GovernanceGate().evaluate(context, decision, config)
    report = ReportBuilder().build(context, decision, governance, config)
    paths = ReportBuilder().write(report, output_dir)
    return {"context": context, "decision": decision, "governance": governance, "report": report, "paths": paths}
