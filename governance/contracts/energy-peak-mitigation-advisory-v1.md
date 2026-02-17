# Decision Contract — Energy Peak Mitigation Advisory (v1)

**Decision class:** `energy_peak_mitigation_advisory`  
**Scope:** BIW Doorline — Door Model 3 (high reinforcement)  
**Mode:** Advisory (recommendations only)

## Intent
Prevent energy peaks (demand spikes) by shaping loads while preserving safety and quality.

## Inputs (required)
- `door_id` (string)
- `door_model` (enum): `MODEL_3_HIGH_REINFORCEMENT`
- `line_id` (string)
- `station_id` (string)
- `window_sec` (int)
- `telemetry` (object), includes at minimum:
  - `peak_kw` (float)
  - `energy_kwh` (float)
  - `cycle_time_sec` (float)
  - `hold_rate` (float, 0..1)
  - `retry_rate` (float, 0..1)
  - `electrode_life_remaining_pct` (float, 0..100)
  - `weld_signature_drift` (float, 0..1)

## Outputs
- `recommendation` (object)
  - `action` (enum): `KEEP` | `SHAPE_LOAD` | `DEFER_NONCRITICAL` | `REQUEST_MAINTENANCE_CHECK`
  - `parameters` (object, optional)
  - `confidence` (float 0..1)
  - `reason` (string)
  - `evidence` (array of objects)
- `constraints_applied` (array of strings)
- `verdict` (enum): `RECOMMEND` | `BLOCK`

## Guardrails (hard constraints)
1. **Quality protection**
   - If `weld_signature_drift >= 0.20` → `verdict = BLOCK` with reason `QUALITY_GUARD_WELD_DRIFT`.
2. **Process stability prerequisites**
   - If `hold_rate > 0.03` → `verdict = BLOCK` with reason `PROCESS_UNSTABLE_HOLD_RATE`.
   - If `retry_rate > 0.02` → `verdict = BLOCK` with reason `PROCESS_UNSTABLE_RETRY_RATE`.
3. **Tooling / wear protection**
   - If `electrode_life_remaining_pct < 15` → `verdict = BLOCK` with reason `TOOLING_GUARD_ELECTRODE_WEAR`.
4. **Approved envelope (conservative defaults)**
   - `limit_concurrent_welds = 2` (load shaping)
   - No suggestion may increase cycle time beyond agreed SLA (advisory must state trade-off explicitly).

## Decision logic (high-level)
- If guardrails pass:
  - Recommend `KEEP` if peak is below limit.
  - Else recommend `SHAPE_LOAD` (bounded) to flatten peaks:
    - `limit_concurrent_welds: 2`
    - optional `schedule_offset_ms <= 600` if supported locally
  - Recommend `DEFER_NONCRITICAL` for auxiliary consumers when peak persists.

## Traceability requirements
Same as v1 traceability: emit JSONL with decision metadata, summarized inputs, and bounded recommendation.
