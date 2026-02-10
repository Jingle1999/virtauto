# Decision Trace (Explainability v1)

This document is **normative documentation** for virtauto’s Decision Trace artifacts.
It must remain **reference-only** (no inline decision payloads), so governance checks can validate it safely.

**Core principle:**
> No decision may pass governance without a trace.  
A trace is the minimal proof that a decision was evaluated under constraints, authority, and policy — and that a **BLOCK** is always possible and explainable.

---

## 1) Canonical artifact paths (preferred)

**Primary (canonical):**
- `ops/reports/decision_trace.jsonl`

**Accepted legacy fallbacks (validator may accept):**
- `ops/decision_trace.jsonl`
- `ops/reports/decision_trace.json`
- `ops/decision_trace.json`

If multiple files exist, the validator will use the first matching candidate path.

---

## 2) What “Decision Trace” means here

The Decision Trace is an **append-only** log of decision processing steps.
It is the evidence backbone for:
- explainability (“why allowed / held / blocked”)
- auditability (“what evidence, what policy, what authority”)
- governance (“no silent execution”)

This file (`decision_trace.md`) is the **documentation** for the trace contract.
The actual machine-readable trace lives in `decision_trace.jsonl`.

---

## 3) Accepted trace formats (validator-level)

To remain tolerant to legacy evolution, the validator accepts two formats:

### A) Record format (recommended) — JSONL
Each line is one JSON object (one event/record).

**Required (after normalization):**
- `ts` *(string; ISO8601 UTC recommended)*
- `trace_version` *(string)*
- `decision_id` *(string)*
- `actor` *(string)*
- `phase` *(string)*
- `result` *(any JSON type; object recommended)*

### B) Bundle format (tolerated) — JSON object (or list of objects)
A “bundle” is one generated trace object that contains inputs + outputs.

**Required:**
- `trace_id` *(string)*
- `inputs` *(non-empty list)*
- `outputs` *(non-empty list)*
- `generated_at` **or** `ts` *(string)*

**Recommended:**
- `because`
- `evidence`

---

## 4) Minimal phase vocabulary (record format)

Recommended phases:

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

## 5) What the trace must prove (Explainability v1)

A valid trace must make the following verifiable:

1. **Decision identity**
   - A stable `decision_id` exists for the decision instance.

2. **Constraints & evidence were checked**
   - A deterministic check step exists (typically in `execute`) that references evidence
     (or marks evidence as missing).

3. **Governance & authority were enforced**
   - Authority enforcement is visible (e.g., `authority_enforcement`)
   - Guardian or invariant checks are visible (e.g., `guardian_precheck` / `guardian_postcheck`)

4. **A stable verdict exists**
   - The decision ends with a logically stable outcome: `ALLOW`, `HOLD`, or `BLOCK`
     (typically in `finalize` or `blocked`).

5. **BLOCK is explicit (not implicit)**
   When the system blocks, the trace must show:
   - the blocking reason (e.g., `missing_required_evidence:*`)
   - the applied policy/invariant
   - the resulting safe state update (e.g., `door.state = HOLD`)

---

## 6) Canonical BLOCK expectations

A BLOCK is considered correct and “successful” if:

- the missing/invalid condition is explicit (e.g., evidence chain incomplete)
- guardian/policy check is recorded and **FAIL**
- no silent override occurs
- a safe state update is recorded (e.g., HOLD / inspection buffer)
- a next action can be proposed (ticket / inspection) without executing physical actions

BLOCK is not a failure of autonomy — it is a **proof of governance**.

---

## 7) Validator reference (governance gate)

Decision trace validation is executed by:

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

## 8) Operational rules (non-negotiables)

- The trace is **append-only** (no history rewriting).
- PR-only changes for governed artifacts.
- No decision reaches execution without trace coverage.
- The trace is the public evidence backbone for the “Industry Model” proof object.

---

## 9) Contract compatibility (important)

Decision Contracts (v1) expect decision identifiers to be **strings** (references), not embedded payloads.

Therefore:
- This `decision_trace.md` MUST stay **reference-only** (no inline decision objects).
- Structured decision details belong in `ops/reports/decision_trace.jsonl` as trace records/bundles.
