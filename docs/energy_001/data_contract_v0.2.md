# ENERGY-001 Minimum Viable Data Contract v0.2

**Status:** Implemented for synthetic offline evaluation only, 2026-11-10.

## Decision semantics (correction to v0.1)

- `analysis_horizon_min`: **conditional ex-post** scenario horizon, not a real-time restart forecast. Never used to authorize a state transition.
- `guaranteed_restart_notice_min`: test-scenario assumption, evidence-labelled. `ASSUMED` is not a verified plant guarantee. Unknown uses `{"value":null,"evidence":"UNKNOWN"}`.
- `alternatives[].scenario_feasibility`: ALLOW/HOLD/BLOCK under **synthetic scenario assumptions**, with known violations BLOCK and missing critical context HOLD. ALLOW here is *not* a plant execution authorization.
- `alternatives[].realtime_status`: synthetic advisory gate, conservatively HOLD for scenario-eligible switches because no verified industrial authorization is provided; known violations remain BLOCK.
- `governance.conditional_preferred_state`: lowest energy of scenario-feasible alternatives (conditional simulation only).
- `governance.realtime_recommended_state`: READY baseline (no change); `governance.execution_permitted=false` always.
- `selected_action`: aggregate gate for **proposed standby state changes**, not a statement that READY is unsafe: BLOCK when both changes are blocked, otherwise HOLD (v0.2 never authorizes real-world transitions).
- `expected_outcome`: **conditional** kWh and energy-only avoided cost; `net_benefit_eur=null` because production/restart economic costs are unknown. `actual_outcome={}`; `realised_savings_claim=false`.

## Inputs

See `tests/fixtures/energy_001/s01.json`, `s02.json`, `s03.json`. Three alternatives READY/ECO/DEEP_ECO with power kW, transition kWh and restart minutes. Trigger, thermal permission, state approval, guaranteed notice and energy price are evidence-labelled. Exactly three unique states. Nonnegative numeric values. `synthetic=true`, `advisory_only=true`, `analysis_horizon_semantics=CONDITIONAL_EX_POST_ONLY`.

## Limits

This is not an industrial safety assessment, an equipment operating instruction, an ex-ante economic forecast or a verified customer saving. No PLC/API/browser/agent changes. The scenarios test code and governance semantics, not actual thermal or restart performance.

## P0 addendum – reviewed semantics (2026-11-10)

- `scenario_feasibility=ALLOW` is explicitly labelled `scenario_feasibility_scope=CONDITIONAL_SYNTHETIC_ONLY`, **not** an industrial permission to operate. `realtime_status` remains HOLD for scenario-eligible changes, and `execution_permitted=false`.
- `alternatives[].reasons` contains specific human-readable reasons, including the state, restart duration and available assumed notice, instead of a generic constraint violation code.
- `energy_cost_eur` and `conditional_avoided_energy_cost_eur` represent **conditional energy-only costs**, not verified monetary savings or net benefit. `production_impact_cost_eur=null` and `net_benefit_eur=null` remain unknown.
- READY is not recommended if its own baseline constraints are HOLD or BLOCK. In that case `realtime_recommended_state=null`; this does not authorize an alternative state.
- Synthetic `ASSUMED` evidence is never promoted to real-world VERIFIED evidence by the evaluator. No physical state change is authorized.
