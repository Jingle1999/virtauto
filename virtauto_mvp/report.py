from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape

from .models import DecisionEvaluation, DecisionReport, GovernanceResult, IndustrialContext


class ReportBuilder:
    version = "0.1.0"

    def build(
        self,
        context: IndustrialContext,
        decision: DecisionEvaluation,
        governance: GovernanceResult,
        config: dict,
    ) -> DecisionReport:
        selected = next(
            (
                option
                for option in decision.options
                if option.option_id == governance.recommended_option_id
            ),
            decision.options[0],
        )

        peak = max(
            context.trigger["peak_events"],
            key=lambda item: item["maximum_power_kw"],
            default=None,
        )

        price_eur_per_kwh = context.energy.get(
            "assumed_price_eur_per_kwh"
        )

        energy_above_threshold_kwh = (
            peak.get("energy_above_threshold_kwh")
            if peak
            else None
        )

        estimated_excess_energy_cost_eur = None
        if (
            energy_above_threshold_kwh is not None
            and price_eur_per_kwh is not None
        ):
            estimated_excess_energy_cost_eur = round(
                energy_above_threshold_kwh * price_eur_per_kwh,
                2,
            )

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
                "peak_severity": (
                    peak.get("severity")
                    if peak
                    else "NONE"
                ),
                "recommendation_status": decision.recommendation.get(
                    "status"
                ),
            },
            situation={
                "trigger": context.trigger["type"],
                "severity": (
                    peak.get("severity")
                    if peak
                    else context.trigger["severity"]
                ),
                "peak_detected": peak is not None,
                "peak_start": peak.get("start") if peak else None,
                "peak_end": peak.get("end") if peak else None,
                "peak_duration_minutes": (
                    peak.get("duration_minutes")
                    if peak
                    else 0
                ),
                "maximum_power_kw": (
                    peak.get("maximum_power_kw")
                    if peak
                    else context.energy["maximum_power_kw"]
                ),
                "average_peak_power_kw": (
                    peak.get("average_power_kw")
                    if peak
                    else None
                ),
                "threshold_kw": context.energy["peak_threshold_kw"],
                "excess_kw": (
                    peak.get("excess_kw")
                    if peak
                    else 0
                ),
                "energy_above_threshold_kwh": (
                    energy_above_threshold_kwh
                ),
                "assumed_price_eur_per_kwh": price_eur_per_kwh,
               "estimated_excess_energy_cost_eur": (
                   estimated_excess_energy_cost_eur
                ),
                "peak_event_count": context.energy.get(
                    "peak_event_count",
                    0,
                ),
                "average_power_kw": context.energy.get(
                    "average_power_kw"
                ),
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
                "score": selected.score,
                "confidence": selected.confidence,
                "status": selected.status,
                "risks": selected.risks,
                "constraints": selected.constraints,
            },
            expected_impact=selected.expected_effects,
            alternatives=[
                option.model_dump()
                for option in decision.options
            ],
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
                "decision_type": decision.decision_type,
                "execution_mode": decision.execution_mode,
                "baseline_option_id": decision.baseline_option_id,
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
