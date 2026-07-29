from __future__ import annotations

from datetime import datetime, timezone
from .models import DecisionEvaluation, DecisionOption, IndustrialContext


class DecisionEngineV1:
    version = "0.1.0"

    def evaluate(self, context: IndustrialContext, config: dict) -> DecisionEvaluation:
        decision_id = f"DEC-{context.dataset_id}"
        baseline = DecisionOption(
            option_id="OPT-000",
            option_type="MAINTAIN_CURRENT_OPERATION",
            title="Betrieb unverändert fortführen",
            expected_effects={"peak_reduction_kw": 0.0, "expected_delay_minutes": 0, "expected_oee_change": 0.0},
            risks={"production": "LOW", "quality": "LOW", "energy": "HIGH" if context.trigger["active"] else "LOW"},
            score=55.0 if context.trigger["active"] else 90.0,
            status="FEASIBLE",
            confidence="HIGH",
            explanation="Baseline for comparison; no operational intervention is made.",
        )
        options = [baseline]
        if context.trigger["active"]:
            max_excess = max(p["excess_kw"] for p in context.trigger["peak_events"])
            for index, asset in enumerate(config.get("assets", {}).get("flexible_loads", []), start=1):
                if not asset.get("operationally_deferrable"):
                    continue
                reduction = min(float(asset["estimated_reduction_kw"]), max_excess)
                ratio = reduction / max_excess if max_excess else 0
                peak_score = min(100.0, ratio * 100)
                score = round(0.25 * 100 + 0.20 * 100 + 0.20 * peak_score + 0.15 * 100 + 0.10 * 95 + 0.10 * 40, 2)
                options.append(DecisionOption(
                    option_id=f"OPT-{index:03d}",
                    option_type="DEFER_FLEXIBLE_LOAD",
                    title=f"{asset['name']} zeitlich verschieben",
                    expected_effects={
                        "target_asset": asset["asset_id"],
                        "peak_reduction_kw": round(reduction, 2),
                        "remaining_excess_kw": round(max(0.0, max_excess - reduction), 2),
                        "duration_minutes": min(asset["max_deferral_minutes"], config["governance"]["max_shift_minutes"]),
                        "expected_delay_minutes": 0,
                        "expected_oee_change": 0.0,
                    },
                    risks={"production": "LOW", "quality": "LOW", "material_flow": "LOW"},
                    score=score,
                    status="FEASIBLE",
                    confidence="MEDIUM",
                    explanation="A known non-critical flexible load can reduce the peak without directly changing the production process.",
                ))
        ranked = sorted(options, key=lambda item: item.score or 0, reverse=True)
        recommended = ranked[0]
        improvement = (recommended.score or 0) - (baseline.score or 0)
        if not context.trigger["active"]:
            recommendation = {"status": "NO_ACTION_REQUIRED", "option_id": baseline.option_id, "reason": "No energy peak trigger is active."}
        elif recommended.option_id == baseline.option_id or improvement < 10:
            recommendation = {"status": "MAINTAIN_CURRENT_OPERATION", "option_id": baseline.option_id, "reason": "No intervention improves the baseline sufficiently."}
        else:
            recommendation = {
                "status": "PROVISIONAL",
                "option_id": recommended.option_id,
                "action": recommended.option_type,
                "summary": recommended.title,
                "confidence": recommended.confidence,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        return DecisionEvaluation(
            decision_id=decision_id,
            context_id=context.context_id,
            baseline_option_id=baseline.option_id,
            options=ranked,
            recommendation=recommendation,
        )
