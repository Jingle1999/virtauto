# Decision Trace (Explainability v1)

This document defines the **normative expectations** for the Decision Trace artifacts used by virtauto’s governance gates.

**Core principle:**  
> No decision may pass governance without a trace.  
A trace is the minimal proof that a decision was evaluated under constraints, authority, and policy — and that a **BLOCK** is always possible and explainable.

---

## 1) Canonical artifact paths (preferred)

**Primary (canonical):**
- `ops/reports/decision_trace.jsonl`

**Accepted legacy fallbacks (validator will also accept):**
- `ops/decision_trace.jsonl`
- `ops/reports/decision_trace.json`
- `ops/decision_trace.json`

If multiple files exist, the validator will use the first matching candidate path.

---

## 2) Accepted formats

The governance gate allows two formats in order to remain tolerant to legacy evolution:

### A) Record format (recommended) — JSONL
Each line is one JSON object (one event/record).

**Required (after normalization):**
- `ts` *(string; ISO8601 UTC recommended)*
- `trace_version` *(string)*
- `decision_id` *(string)*
- `actor` *(string)*
- `phase` *(string)*
- `result` *(any JSON type; object recommended)*

### B) Bundle format (tolerated) — single JSON object or list
A “bundle” is one generated trace object that already contains inputs + outputs.

**Required:**
- `trace_id`
- `inputs` *(non-empty list)*
- `outputs` *(non-empty list)*
- `generated_at` **or** `ts`

**Recommended:**
- `because`
- `evidence`

---

## 3) Minimal phase vocabulary

The record format should use phases from this minimal set:

- `route`
- `guardian_precheck`
- `authority_enforcement`
- `execute`
- `guardian_postcheck`
- `finalize`
- `blocked`

Legacy synonyms may appear (accepted but should be migrated):
- `guardrail`, `precheck`, `postcheck`

---

## 4) What the trace must prove (Explainability v1)

A valid trace must make the following verifiable:

1. **Decision identity**  
   The trace clearly references a `decision_id` for the decision instance.

2. **Constraints & evidence were checked**  
   The trace includes a deterministic check step (typically in `execute`) that references evidence or marks evidence as missing.

3. **Governance and authority were enforced**  
   The trace includes a governance step (e.g., `authority_enforcement`) and/or a guardian step.

4. **A verdict exists**  
   The trace ends with an outcome that is logically stable: `ALLOW`, `HOLD`, or `BLOCK` (typically in `finalize`).

5. **BLOCK is explicit (not implicit)**  
   When the system blocks, the trace must contain:
   - the blocking reason (e.g., `missing_required_evidence:*`)
   - the applied policy/invariant
   - the resulting safe state update (e.g., `door.state = HOLD`)

---

## 5) Canonical BLOCK trace expectations

A BLOCK is considered correct and “successful” if:

- The missing/invalid condition is explicit (e.g., evidence chain incomplete)
- Guardian/policy check is recorded and **FAIL**
- No silent override occurs
- A safe state update is recorded (e.g., HOLD / inspection buffer)
- A next action can be proposed (ticket / inspection) without executing physical actions

BLOCK is not a failure of autonomy — it is a **proof of governance**.

---

## 6) Validator reference (governance gate)

The decision trace is validated by:

- `ops/validate_decision_trace.py`

The validator checks:
- trace file exists in one of the candidate paths
- file is non-empty
- last N entries are valid under one of the accepted formats
- required keys exist and basic types are sane
- phases are either allowed or warned

Exit codes:
- `0` = OK
- `1` = FAIL (blocking)

---

## 7) Operational rules (non-negotiables)

- The trace is **append-only** (no history rewriting).
- PR-only changes for governed artifacts.
- No decision should reach execution without trace coverage.
- The trace is the public evidence backbone for the “Industry Model” proof object.

---

## Appendix: Example (record format, JSONL)

See: `ops/reports/decision_trace.jsonl` for the current canonical examples.
