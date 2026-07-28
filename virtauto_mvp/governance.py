from __future__ import annotations

from datetime import datetime, timedelta, timezone
from .models import DecisionEvaluation, GovernanceResult, IndustrialContext


class GovernanceGate:
    version = "0.1.0"

    def evaluate(self, context: IndustrialContext, decision: DecisionEvaluation, config: dict) -> GovernanceResult:
        rules = []
        conditions: list[str] = []
        status = "ALLOW_ADVISORY"
        selected = next((o for o in decision.options if o.option_id == decision.recommendation.get("option_id")), None)

        def apply(rule_id: str, passed: bool, failure: str, explanation: str) -> None:
            nonlocal status
            result = "PASS" if passed else failure
            rules.append({"rule_id": rule_id, "result": result, "explanation": explanation})
            if not passed:
                if failure == "BLOCK":
                    status = "BLOCK"
                elif failure == "HOLD" and status != "BLOCK":
                    status = "HOLD_FOR_REVIEW"

        apply("GOV-DATA-001", context.data_quality.decision_readiness != "INSUFFICIENT", "HOLD", "The dataset must be decision-capable.")
        apply("GOV-EXEC-001", config["governance"]["execution_mode"] == "PROPOSE_ONLY", "BLOCK", "Only advisory execution is permitted.")
        apply("GOV-QUALITY-001", context.quality.get("status") != "CRITICAL" and context.quality.get("quality_gate_open") is True, "BLOCK", "Critical quality conditions block production-related advice.")
        fill = context.material_flow["buffer_level_units"] / context.material_flow["buffer_capacity_units"]
        apply("GOV-BUFFER-001", fill >= config["governance"]["min_buffer_fill_ratio"], "HOLD", "Buffer fill must remain above the configured minimum.")

        if decision.recommendation.get("status") == "NO_ACTION_REQUIRED":
            status = "NO_ACTION_REQUIRED"
        elif decision.recommendation.get("status") == "MAINTAIN_CURRENT_OPERATION":
            status = "NO_ACTION_REQUIRED"
        elif selected and selected.option_type == "DEFER_FLEXIBLE_LOAD":
            conditions.append(f"Production Manager confirms that {selected.expected_effects.get('target_asset')} is operationally deferrable.")
            status = "ALLOW_ADVISORY_WITH_CONDITIONS" if status == "ALLOW_ADVISORY" else status

        valid_until = None
        if status.startswith("ALLOW"):
            valid_until = (datetime.now(timezone.utc) + timedelta(minutes=config["governance"]["advisory_validity_minutes"])).isoformat()
        return GovernanceResult(
            status=status,
            decision_id=decision.decision_id,
            recommended_option_id=decision.recommendation.get("option_id"),
            conditions=conditions,
            required_approvals=[config["governance"]["decision_owner"]],
            required_reviews=config["governance"].get("required_reviewers", []),
            veto_roles=config["governance"].get("veto_roles", []),
            rule_results=rules,
            execution_mode=config["governance"]["execution_mode"],
            valid_until=valid_until,
        )
