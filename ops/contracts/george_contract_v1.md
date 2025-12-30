# GEORGE Contract v1 (Frozen)

Version: v1
Status: FROZEN
Applies to: ops/george_orchestrator_v2.py and all runtime gates / UI readers

## Truth Sources (Single Source of Truth)
- Canonical system state file: ops/system_status.json
- Canonical latest decision file: ops/decisions/latest.json
- Canonical decision trace stream: ops/reports/decision_trace.jsonl

No other file may be treated as authoritative by the website or gates.

## Output Guarantees (Hard)
For every GEORGE run that produces a decision:
1) ops/decisions/latest.json MUST be written and must validate against ops/contracts/schemas/decision_latest_v1.schema.json
2) ops/reports/decision_trace.jsonl MUST be appended with deterministic records that validate against
   ops/contracts/schemas/decision_trace_record_v1.schema.json
3) ops/system_status.json MUST exist and validate against ops/contracts/schemas/system_status_v1.schema.json

## “GEORGE NEVER …” (Hard Rules)
- GEORGE never writes/edits website HTML directly.
- GEORGE never bypasses Guardian or Authority enforcement.
- GEORGE never executes actions without writing trace.
- GEORGE never invents status sources: UI reads only ops/system_status.json (+ derived autonomy).
- GEORGE never writes to unknown/undocumented files outside ops/{decisions,reports,system_status.json,status.json internal health}.

## Decision Classes (Allowed Values)
- safety_critical
- operational
- strategic
- deploy

## Status Vocabulary (Allowed Values)
Decision status:
- pending
- success
- error
- blocked

System/Agent state:
- ok
- degraded
- blocked
- unknown

Autonomy mode:
- supervised
- advisory
- enforced

## Gate Compatibility Contract
ops/decisions/latest.json MUST contain:
- decision_id (string)
- decision_class (enum)
- authority_source (string)
- health_context.system_health (0..100)
- health_context.guardian_status (OK|DEGRADED|DOWN)
- decision_trace (object, complete + trace_id + execution_path[])
- trace (alias object, id/trace_id/path/execution_path)
- signals.system_health_score (0..1)
- signals.guardian_ok (bool)
- signals.status_endpoint_ok (bool)
- signals.decision_trace_present (bool)

## Trace Determinism
Trace must contain these phases (at least once each, in order for a run):
- route
- guardian_precheck
- authority_enforcement
- execute (or blocked)
- guardian_postcheck
- finalize

Each record must include:
- ts (ISO UTC)
- trace_version ("v1")
- decision_id
- actor
- phase
- result

## Backward Compatibility
Legacy files may exist but are not authoritative:
- ops/status.json (internal health persistence only)
- ops/reports/system_status.json (deprecated; not truth)
- status/status.json (deprecated; not truth)

## Enforcement
Contract tests must run in CI. Any violation = FAIL.
