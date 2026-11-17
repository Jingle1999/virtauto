"""Isolated synthetic ENERGY-001 evaluator; no plant control or execution."""
from __future__ import annotations

from decimal import Decimal
from virtauto_core.decision_object import DecisionObject

STATES = ("READY", "ECO", "DEEP_ECO")
EVIDENCE = {"VERIFIED", "ASSUMED", "UNKNOWN"}


def _evidence(item, label):
    if not isinstance(item, dict) or item.get("evidence") not in EVIDENCE or "value" not in item:
        raise ValueError(f"Invalid evidence field: {label}")
    if (item["evidence"] == "UNKNOWN") != (item["value"] is None):
        raise ValueError(f"UNKNOWN must have null value, and known values must be non-null: {label}")
    return item["value"]


def _number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value < float("inf"):
        raise ValueError(f"Invalid nonnegative number: {label}")
    return Decimal(str(value))


def evaluate_energy_001(payload: dict) -> DecisionObject:
    if not isinstance(payload, dict) or payload.get("synthetic") is not True or payload.get("advisory_only") is not True:
        raise ValueError("v0.2 requires synthetic=true and advisory_only=true")
    if payload.get("analysis_horizon_semantics") != "CONDITIONAL_EX_POST_ONLY":
        raise ValueError("Analysis horizon must be conditional, not a forecast")
    horizon = _number(payload["analysis_horizon_min"], "analysis_horizon_min")
    if horizon == 0: raise ValueError("Analysis horizon must be positive")
    trigger = payload["trigger"]
    stop = _evidence(trigger["stop_confirmed"], "stop_confirmed")
    welding = _evidence(trigger["welding_active"], "welding_active")
    if stop is not None and not isinstance(stop, bool): raise ValueError("stop_confirmed must be boolean")
    if welding is not None and not isinstance(welding, bool): raise ValueError("welding_active must be boolean")
    if trigger["current_state"] != "READY": raise ValueError("v0.2 models READY baseline only")
    ctx = payload["decision_context"]
    notice = _evidence(ctx["guaranteed_restart_notice_min"], "guaranteed_restart_notice_min")
    if notice is not None: notice = _number(notice, "guaranteed_restart_notice_min")
    price = _evidence(ctx["energy_price_eur_per_kwh"], "energy_price_eur_per_kwh")
    if price is not None: price = _number(price, "energy_price_eur_per_kwh")
    rows = payload["alternatives"]
    if not isinstance(rows, list) or len(rows) != 3 or {a["state"] for a in rows} != set(STATES):
        raise ValueError("Exactly three unique READY/ECO/DEEP_ECO alternatives required")
    evaluated = []
    for state in STATES:
        a = next(a for a in rows if a["state"] == state)
        power = _number(a["power_kw"], "power_kw")
        transition = _number(a["transition_energy_kwh"], "transition_energy_kwh")
        restart = _number(a["restart_duration_min"], "restart_duration_min")
        energy = power * horizon / Decimal(60) + transition
        thermal = _evidence(ctx["thermal_permission"][state], f"thermal_permission.{state}")
        approval = _evidence(ctx["state_approval"][state], f"state_approval.{state}")
        for label, value in [("thermal", thermal), ("approval", approval)]:
            if value is not None and not isinstance(value, bool): raise ValueError(f"{label} must be boolean")
        reasons = []
        if state == "READY":
            if thermal is False:
                reasons.append("READY baseline prohibited by thermal constraint")
            if approval is False:
                reasons.append("READY baseline lacks state approval")
            if thermal is None:
                reasons.append("READY thermal permission is UNKNOWN")
            if approval is None:
                reasons.append("READY state approval is UNKNOWN")
            status = "BLOCK" if thermal is False or approval is False else "HOLD" if thermal is None or approval is None else "ALLOW"
        else:
            if stop is False: reasons.append("Production stop is not confirmed: stop_confirmed=false")
            if welding is True: reasons.append("Welding remains active: welding_active=true")
            if thermal is False: reasons.append(f"{state} is prohibited by thermal constraint")
            if approval is False: reasons.append(f"{state} lacks state approval")
            if notice is not None and restart > notice:
                reasons.append(f"{state} requires {restart:g} min to restart, but only {notice:g} min of restart notice is assumed")
            blocked = bool(reasons)
            if not blocked:
                if stop is None: reasons.append("Production stop confirmation is UNKNOWN")
                if welding is None: reasons.append("Welding activity is UNKNOWN")
                if thermal is None: reasons.append(f"{state} thermal permission is UNKNOWN")
                if approval is None: reasons.append(f"{state} state approval is UNKNOWN")
                if notice is None: reasons.append("Guaranteed restart notice is UNKNOWN")
            status = "BLOCK" if blocked else "HOLD" if reasons else "ALLOW"
            if status == "ALLOW":
                reasons.append("Conditionally feasible under synthetic scenario assumptions only; no operational authorization")
        realtime = "HOLD" if state != "READY" and status == "ALLOW" else status
        if state != "READY" and status == "ALLOW":
            reasons.append("Realtime gate: assumed evidence cannot authorize a physical state change")
        evaluated.append({"state": state, "scenario_feasibility": status,
                          "scenario_feasibility_scope": "CONDITIONAL_SYNTHETIC_ONLY",
                          "realtime_status": realtime, "energy_kwh": float(energy),
                          "energy_cost_eur": float(energy * price) if price is not None else None,
                          "energy_cost_semantics": "CONDITIONAL_ENERGY_ONLY_NOT_NET_BENEFIT",
                          "restart_duration_min": float(restart), "reasons": reasons})
    baseline = evaluated[0]["energy_kwh"]
    # Conditional ranking only among alternatives not violating known constraints.
    candidates = [a for a in evaluated if a["scenario_feasibility"] == "ALLOW"]
    winner = min(candidates, key=lambda a: (a["energy_kwh"], STATES.index(a["state"]))) if candidates else None
    conditional = winner["state"] if winner else None
    changes = evaluated[1:]
    gate = "BLOCK" if all(a["realtime_status"] == "BLOCK" for a in changes) else "HOLD"
    # Even when scenario assumptions allow a change, they cannot authorize a real-world switch.
    savings = float(Decimal(str(baseline)) - Decimal(str(winner["energy_kwh"]))) if winner else None
    cost_savings = float(Decimal(str(savings)) * price) if savings is not None and price is not None else None
    return DecisionObject(
        decision_id=f"ENERGY-001-{payload['scenario_id']}", decision_type="ENERGY_AWARE_STANDBY",
        timestamp=payload["decision_timestamp"], selected_action=gate,
        context={"scenario_id": payload["scenario_id"], "equipment_id": payload["equipment_id"], "synthetic": True, "advisory_only": True, "analysis_horizon_min": float(horizon), "analysis_horizon_semantics": "CONDITIONAL_EX_POST_ONLY"},
        governance={"conditional_preferred_state": conditional, "realtime_recommended_state": ("READY" if evaluated[0]["realtime_status"] == "ALLOW" else None), "baseline_status": evaluated[0]["realtime_status"], "realtime_change_gate": gate, "human_authorization_required": True, "execution_permitted": False, "reason": "Synthetic assumptions and hindsight horizon cannot authorize an operational switch"},
        evidence=[{"field": "guaranteed_restart_notice_min", "status": ctx["guaranteed_restart_notice_min"]["evidence"]}, {"field": "thermal_permission", "status": {s:ctx["thermal_permission"][s]["evidence"] for s in STATES}}],
        alternatives=evaluated,
        expected_outcome={"conditional_energy_saving_kwh": savings, "conditional_avoided_energy_cost_eur": cost_savings, "cost_semantics": "CONDITIONAL_AVOIDED_ENERGY_COST_ONLY", "production_impact_cost_eur": None, "net_benefit_eur": None, "realised_savings_claim": False}, actual_outcome={},
        contract={"id": "ENERGY-001", "version": "v0.2-p0", "execution_mode": "PROPOSE_ONLY"},
    )
