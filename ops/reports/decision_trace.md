# Decision Trace — Update `ops/status_agent.py` 

## Summary
This change upgrades the Status Agent’s truth regeneration to include **trace coverage computation** and makes the decision trace outputs **audit-complete**.

**Goal:** Increase governance verifiability by:
- declaring all required truth artifacts as outputs in the trace, and
- computing a deterministic `trace_coverage` value from the last N trace entries.

---

## Decision
**APPROVE** the update to `ops/status_agent.py` that:
1. Extends `decision_trace.outputs` to include:
   - `ops/reports/system_status.json`
   - `ops/decisions/gate_result.json`
   - `ops/reports/decision_trace.json`
   - `ops/reports/decision_trace.jsonl`
2. Adds deterministic computation of `trace_coverage` from `ops/reports/decision_trace.jsonl`
3. Exposes `--trace-window` to control the evaluation window (default: 20)

---

## Why this is safe
- **No network calls.** Reads only from repo-local files.
- **Deterministic.** Same repo state + same inputs → same outputs.
- **Additive.** Does not require other agents; only improves evidence quality.
- **Conservative gating unchanged.** Emergency lock still forces `DENY`.

---

## Scope of change
### Files changed
- `ops/status_agent.py`

### Behavioural changes
- `system_status.json` now includes a real numeric:
  - `autonomy_score.trace_coverage`
- `decision_trace.json` and `.jsonl` now declare all truth artifacts as explicit outputs.
- Trace coverage is calculated as the fraction of recent trace entries that satisfy minimal audit requirements.

---

## Inputs / Outputs
### Inputs (read)
- `ops/autonomy.json` (optional; used for autonomy percent)
- `ops/decisions/latest.json` (optional; link only)
- `ops/emergency_lock.json` (optional; gate decision)
- `ops/reports/decision_trace.jsonl` (optional; used for trace coverage; missing → coverage 0.0)

### Outputs (written/refreshed)
- `ops/reports/system_status.json`
- `ops/reports/decision_trace.json`
- `ops/reports/decision_trace.jsonl` (append-only)
- `ops/decisions/gate_result.json`
- `ops/agent_activity.jsonl` (append-only)

---

## Audit rule: Trace coverage definition (Option A)
`trace_coverage` is computed over the last `N` entries of `ops/reports/decision_trace.jsonl` (default `N=20`):

A trace entry counts as **covered** if:
- it is valid JSON, and
- contains required keys:
  - `schema_version`, `generated_at`, `trace_id`, `because`, `inputs`, `outputs`, `evidence`
- and its `outputs` include all required truth artifacts:
  - `ops/reports/system_status.json`
  - `ops/decisions/gate_result.json`
  - `ops/reports/decision_trace.json`
  - `ops/reports/decision_trace.jsonl`

Result:
- `trace_coverage = covered / total` rounded to 3 decimals
- if no entries exist → `0.0`

---

## Gate logic (unchanged)
- If `ops/emergency_lock.json` contains `"locked": true` → `gate_verdict = DENY`
- Else → `gate_verdict = ALLOW`

---

## Evidence
- `ops/reports/decision_trace.jsonl` (append-only audit log)
- `ops/agent_activity.jsonl` (append-only activity log)
- `ops/decisions/gate_result.json` (authoritative gate snapshot)
- `ops/reports/system_status.json` (primary truth artifact rendered by UI)

---

## Acceptance criteria (Pass/Fail)
### PASS if
- Workflow run regenerates all truth artifacts without error
- `system_status.json` contains `autonomy_score.trace_coverage` as a number (0.0–1.0)
- `decision_trace.outputs` lists all four required truth artifacts
- Emergency lock still flips gate to `DENY`

### FAIL if
- Any truth artifact is missing after a run
- Trace outputs omit required artifacts
- Trace coverage is non-deterministic for identical repo state
- Emergency lock no longer forces `DENY`

---

## Rollback plan
Revert the `ops/status_agent.py` change via PR revert.
No data migrations required; logs are append-only.

---

## Final verdict
✅ **APPROVE** — Option A strengthens auditability and makes traceability measurable without changing authority, runtime risk, or operational behavior.
