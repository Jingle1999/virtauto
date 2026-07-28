from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape

from .models import DecisionEvaluation, DecisionReport, GovernanceResult, IndustrialContext


class ReportBuilder:
    version = "0.1.0"

    def build(self, context: IndustrialContext, decision: DecisionEvaluation, governance: GovernanceResult, config: dict) -> DecisionReport:
        selected = next((o for o in decision.options if o.option_id == governance.recommended_option_id), decision.options[0])
        peak = max(context.trigger["peak_events"], key=lambda p: p["maximum_power_kw"], default=None)
        return DecisionReport(
            identity={
                "report_id": f"REP-{context.dataset_id}",
                "decision_id": decision.decision_id,
                "context_id": context.context_id,
                "contract_id": config["governance"]["contract_id"],
                "site_id": context.site_id,
                "area_id": context.area_id,
                "line_id": context.line_id,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "valid_until": governance.valid_until,
                "retention_mode": config["governance"]["retention_mode"],
            },
            executive_decision={
                "status": governance.status,
                "headline": selected.title,
                "confidence": selected.confidence,
                "execution_mode": governance.execution_mode,
            },
            situation={
                "trigger": context.trigger["type"],
                "severity": context.trigger["severity"],
                "maximum_power_kw": peak["maximum_power_kw"] if peak else context.energy["maximum_power_kw"],
                "threshold_kw": context.energy["peak_threshold_kw"],
                "excess_kw": peak["excess_kw"] if peak else 0,
                "analysis_window": context.analysis_window,
            },
            industrial_context={
                "production": context.production,
                "quality": context.quality,
                "material_flow": context.material_flow,
                "order": context.order,
                "summary": context.context_summary,
            },
            recommendation={
                "option_id": selected.option_id,
                "type": selected.option_type,
                "title": selected.title,
                "explanation": selected.explanation,
            },
            expected_impact=selected.expected_effects,
            alternatives=[o.model_dump() for o in decision.options],
            governance=governance.model_dump(),
            data_quality={
                **context.data_quality.model_dump(),
                "context_confidence": context.context_confidence,
                "recommendation_confidence": selected.confidence,
            },
            assumptions=context.uncertainties,
            audit={
                "context_builder_version": "0.1.0",
                "decision_engine_version": "0.1.0",
                "governance_gate_version": "0.1.0",
                "report_builder_version": self.version,
                "options_generated": len(decision.options),
                "rules_evaluated": len(governance.rule_results),
            },
        )

    def write(self, report: DecisionReport, output_dir: str | Path) -> dict[str, str]:
        output = Path(output_dir)
        output.mkdir(parents=True, exist_ok=True)
        json_path = output / "decision_report.json"
        html_path = output / "decision_report.html"
        json_path.write_text(json.dumps(report.model_dump(), indent=2, ensure_ascii=False), encoding="utf-8")
        env = Environment(loader=FileSystemLoader(Path(__file__).parent / "templates"), autoescape=select_autoescape())
        template = env.get_template("report.html")
        html_path.write_text(template.render(report=report.model_dump()), encoding="utf-8")
        return {"json": str(json_path), "html": str(html_path)}
