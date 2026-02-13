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
