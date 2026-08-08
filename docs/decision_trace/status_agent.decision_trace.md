# Decision Trace — Status Agent (Truth Regeneration)

## Scope
This document defines the decision/trace contract for the **Status Agent** (`ops/status_agent.py`).

The Status Agent is a **deterministic truth regenerator** that produces the website’s Single Source of Truth (SSOT) artifacts from local repository evidence. It must **never** self-generate governance permission. It only executes under a **PASS** gate provided by the workflow.

---

## Actor
- **actor:** `status_agent`
- **phase:** `TRUTH_REGENERATION`
- **authority:** supervised truth mutation **only after governance PASS**

---

## Inputs (deterministic)
### Workflow gate inputs (mandatory)
- `STATUS_GATE_VERDICT` = `PASS | BLOCK | UNKNOWN`
- `STATUS_GATE_REASONS` = JSON array string or plain string

### Repository state inputs (best-effort)
- `ops/autonomy.json` (autonomy score input)
- `ops/decisions/latest.json` (latest decision pointer)
- `ops/emergency_lock.json` (hard lock override)
- `ops/authority_matrix.yaml|json` (evidence presence only)
- `ops/george_rules.yaml` (evidence presence only)

---

## Outputs (SSOT + evidence)
- `ops/reports/system_status.json`
- `ops/reports/decision_trace.json`
- `ops/reports/decision_trace.jsonl` (append-only)
- `ops/agent_activity.jsonl` (append-only)

> Note: The Status Agent **does not** write `ops/decisions/gate_result.json` by design.

---

## Decision Model
### Gate semantics
- If `STATUS_GATE_VERDICT != PASS` → the agent:
  - writes trace + activity evidence
  - returns non-zero exit code (BLOCK semantics)

### Emergency lock semantics
- If `ops/emergency_lock.json` contains `{ "locked": true }` → hard block:
  - system_state becomes `BLOCKED`
  - exit code non-zero

### Conservatism principle
- Missing or malformed inputs must **not** increase autonomy or health.
- File evidence is existence/mtime/size only (Phase 1). No content parsing required.

---

## Trace Schema (Decision Trace)
The Status Agent writes:
- `ops/reports/decision_trace.json` (latest snapshot)
- `ops/reports/decision_trace.jsonl` (append-only log)

Minimum required fields:
- `schema_version` (e.g. `1.1`)
- `generated_at` (UTC ISO8601)
- `trace_id` (unique)
- `actor` = `status_agent`
- `phase` = `TRUTH_REGENERATION`
- `gate.verdict` = PASS|BLOCK|UNKNOWN
- `gate.reasons` = array
- `inputs[]`
- `outputs[]`
- `evidence{...}`

---

## Failure Modes and Expected Behavior
1. **Gate not PASS**
   - Trace + activity appended
   - Exit code != 0
2. **Emergency lock active**
   - Trace + activity appended
   - system_status shows BLOCKED
   - Exit code != 0
3. **Malformed JSON inputs**
   - Treat as missing (null)
   - Continue generating conservative truth, never inflate autonomy

---

## Auditability Requirements
- Every run must append one entry to:
  - `ops/reports/decision_trace.jsonl`
  - `ops/agent_activity.jsonl`
- The workflow must archive artifacts as GitHub Actions artifacts (separate from website publishing).
