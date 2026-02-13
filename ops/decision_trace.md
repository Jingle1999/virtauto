# Decision Trace – Introduce Consistency Agent v1 (Website Scope)

## Trace ID
TRACE-2026-02-13-CONSISTENCY-V1

## Context

The virtauto website is governed by a strict Single Source of Truth model:

Intent → Constraints → Decision → Audit → Render

While Status Agent and Guardian enforce runtime truth generation and policy gates, there is currently no deterministic cross-artifact integrity validation across:

- system_status.json  
- decision_trace.jsonl  
- gate_result.json  
- agents/registry.yaml  

This introduces architectural risk:
- broken cross-links could go undetected  
- trace references could become inconsistent  
- registry/state divergence might occur silently  

To maintain auditability and governance-first autonomy, a structural consistency layer is required.

---

## Intent

Introduce a **Consistency Agent v1** that:

- Validates structural integrity of core truth artifacts
- Verifies cross-file link correctness
- Ensures trace_id consistency between gate_result and decision_trace
- Validates registry compliance for active agents
- Blocks merges if violations are detected

Scope: **Website Governance Layer only**  
(Explicitly NOT applied to industrymodel.html or industrial simulation layer.)

---

## Constraints

- Deterministic execution (no network calls)
- CI-compatible
- Read-only validation (no mutation of truth files)
- Fail-closed behavior on structural violations
- Configurable thresholds via YAML (no hard-coded values)
- Must not introduce runtime side effects

---

## Authority

Decision Class: Governance Infrastructure  
Authority Level Required: Maintainer Approval  
Execution Mode: PR + CI validation  
Autonomy Mode: SUPERVISED  

---

## Decision

Approve introduction of:

1. `ops/consistency_agent.py`
2. `ops/consistency_rules.yaml`
3. `.github/workflows/consistency-agent.yml`

The Consistency Agent becomes:

- A required CI check for main branch
- A structural integrity guardrail
- A precondition for future Execution Control Layer evolution

---

## Risk Assessment

Low operational risk  
Medium governance impact (merge-blocking capability)

Mitigation:
- Clear error codes
- Tail-window validation (bounded performance)
- Strict separation from industrial execution logic

---

## Expected Outcomes

If PASS:
- Website truth-chain integrity guaranteed
- Trace continuity enforced
- Governance becomes formally self-consistent

If FAIL:
- Merge blocked
- Violations explicitly logged
- No silent degradation possible

---

## Outputs

- ops/reports/consistency_report.json (machine-readable)
- GitHub CI summary
- Deterministic exit codes

---

## Governance Positioning

This establishes:

Status Agent → Runtime Truth  
Guardian → Policy Enforcement  
Consistency Agent → Structural Integrity  

This is the final layer required before moving toward:

"GitHub for Industrial Decisions" (Execution Control Layer)

---

## Approval

[ ] Approved  
[ ] Changes required  

Approved by: ____________________  
Date: ____________________
## Conservative Autonomy Score v1 (Evidence-First)

### Intent
Compute a **conservative, deterministic autonomy percentage** that is never higher than what can be justified by local evidence.
Principle: **lower-but-certain beats higher-but-uncertain**.

### Inputs (local, deterministic)
- `ops/autonomy.json` (declared autonomy cap; treated as **upper bound only**)
- `ops/emergency_lock.json` (hard gate clamp)
- `ops/reports/decision_trace.jsonl` (trace presence & recency signal)
- `ops/reports/system_status.json` (generated output; freshness derived from `generated_at`)
- Agent snapshot (in `status_agent.py`, deterministic baseline)

### Method (conservative_autonomy_v1)
We compute:

1) **Gate clamp**
- `gate_factor = 1.0` if `gate_verdict == ALLOW`, else `0.0`

2) **Freshness penalty**
Based on minutes since `generated_at`:
- `<= 15 min` → factor `1.0` (FRESH)
- `15–60 min` → factor `0.5` (STALE)
- `> 60 min` → factor `0.2` (EXPIRED)
If unknown → `0.2`

3) **Trace signal (minimal)**
- If `decision_trace.jsonl` missing → `0.0` (MISSING)
- If present and last record is `<= 15 min` → `1.0` (LINKED_FRESH)
- Else → `0.5` (LINKED_STALE / UNVERIFIED)

4) **Agent coverage**
- `active_agents / total_agents`
- Active is counted only if `status == ok` and `state == ACTIVE`
- `total_agents` is fixed to `6` (dashboard expectation)

5) **Final score**
- `core = min(base_cap_percent, agent_coverage_percent)`
- `evidence_autonomy_percent = round(core * freshness_factor * trace_factor * gate_factor, 1)`

### Output fields
Written to `ops/reports/system_status.json` under:
- `autonomy_score.percent`
- `autonomy_score.details` (cap, coverage, freshness, trace labels)

Additionally, the full derivation is recorded in:
- `ops/reports/decision_trace.json` and appended to `ops/reports/decision_trace.jsonl`
under evidence: `ev_autonomy_score.details`.

### Safety posture
- Never exceeds declared autonomy (`ops/autonomy.json`) because it is used only as a **cap**.
- Never exceeds what is supported by **coverage**.
- Strongly degrades under **staleness** or missing trace.
- Hard-clamps to **0%** on emergency lock (DENY).

### Addition to industrymodel.html PR#545
- Slight change of wording needed for better process-understanding
