# Decision Contract — Energy Output Stability Advisory (v1)

**Decision class:** `energy_output_stability_advisory`  
**Scope:** BIW Doorline — Door Model 2 (mixed material)  
**Mode:** Advisory (recommendations only)

## Intent
Stabilize energy usage by keeping the process within an approved stability envelope while maintaining throughput and quality constraints.

## Inputs (required)
- `door_id` (string)
- `door_model` (enum): `MODEL_2_MIXED_MATERIAL`
- `line_id` (string)
- `station_id` (string)
- `window_sec` (int)
- `telemetry` (object), includes at minimum:
  - `energy_kwh` (float)
  - `cycle_time_sec` (float)
  - `hold_rate` (float, 0..1)
  - `retry_rate` (float, 0..1)
  - `weld_signature_drift` (float, 0..1)

## Outputs
- `recommendation` (object)
  - `action` (enum): `KEEP` | `ADJUST_HEMMING_SPEED` | `ADJUST_WELD_SCHEDULE` | `REQUEST_MAINTENANCE_CHECK`
  - `parameters` (object, optional)
  - `confidence` (float 0..1)
  - `reason` (string)
  - `evidence` (array of objects): telemetry references and computed metrics
- `constraints_applied` (array of strings)
- `verdict` (enum): `RECOMMEND` | `BLOCK`

## Guardrails (hard constraints)
1. **Quality protection**
   - If `weld_signature_drift >= 0.20` → `verdict = BLOCK` with reason `QUALITY_GUARD_WELD_DRIFT`.
2. **Stability prerequisites**
   - If `hold_rate > 0.03` → `verdict = BLOCK` with reason `PROCESS_UNSTABLE_HOLD_RATE`.
   - If `retry_rate > 0.02` → `verdict = BLOCK` with reason `PROCESS_UNSTABLE_RETRY_RATE`.
3. **Approved envelope (conservative defaults)**
   - `hemming_speed_delta_pct ∈ [-5, 0]` (only slower or equal hemming speed)
   - `weld_schedule_offset_ms <= 600` (delay-only offset)
   - No parameter may reduce safety or violate any legal constraints.

## Decision logic (high-level)
- If prerequisites and quality guard pass:
  - Prefer `KEEP` if energy variance is within baseline band and cycle time is stable.
  - Else recommend bounded adjustment:
    - `ADJUST_HEMMING_SPEED` with `delta_pct` in `[-5,0]`
    - or `ADJUST_WELD_SCHEDULE` with `offset_ms <= 600`
  - Use `REQUEST_MAINTENANCE_CHECK` when instability indicators trend upward.

## Traceability requirements
Every evaluation must emit a decision trace line (JSONL) including:
- `ts`, `trace_version`, `decision_id`, `decision_class`, `actor`, `phase`
- `inputs` (door_id, station_id, window_sec, summarized telemetry)
- `result` (verdict, recommendation, constraints_applied, reason, confidence)
