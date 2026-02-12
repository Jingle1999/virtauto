# Decision Trace – Content Publish BLOCK Example

**Trace ID:** `trace_content_publish_0001`  
**Decision Class:** CONTENT_PUBLISH  
**Spec Reference:** industrymodel.html#spec-v1  
**Status:** BLOCKED  

---

## Decision Intent
Publish updated website content to the public channel.

---

## Actors Involved
- Content Agent (request)
- GEORGE (orchestration & final decision)
- Guardian (policy enforcement)

---

## Decision Flow

1. **Route**  
   Publish request routed by GEORGE.

2. **Execute**  
   Content Agent prepared static publish plan.

3. **Guardian Check**  
   Policy `CONTENT_PUBLISH_GUARDIAN` applied.  
   All structural checks passed, but required decision trace documentation was missing.

4. **Finalize**  
   Decision blocked.  
   No content published.

---

## Block Reason
Required `decision_trace.md` update missing at time of submission.

---

## Outcome
BLOCKED  
No execution performed.

---

## Governance Principle Demonstrated
> No decision without trace.  
> No execution without explainability.

---

## 2026-02-12 — Agent Registry v1 (Governed Platform Configuration)

**Decision ID:** `gov:agent-registry-v1-2026-02-12`  
**Domain:** `virtauto_platform`  
**Decision Class:** `platform.agent_registry_update`  
**Verdict:** `ALLOW`

### Intent

Create a canonical `agents/registry.yaml` defining all platform agents and their allowed / forbidden actions under PR-only governance.

This formalizes:

- Status Agent (read-only SSOT)
- Content Agent (PR-only updates)
- Audit Agent (validation & advisory)
- Deploy Agent (governed deployment flow)

### Why this decision matters

The agent registry is a governance artifact.  
If an agent is not listed here, it is not part of the system.

This update:

- Introduces a machine-readable authority definition
- Makes agent scope explicit
- Enforces PR-only change discipline
- Prevents direct execution without governance checks

### Governance Enforcement

Required checks:

- `validate_contract_v1`
- `validate_decision_trace`
- `validate_status`
- `review_gate`

Guardian check: `PASS`  
Approval: `1 approving review`  
Policy: PR-only change required for governance artifacts

### Operational Meaning

This decision does **not** deploy new behavior automatically.  
It establishes authority boundaries and control constraints.

It is a configuration governance decision, not an execution decision.

---

**Normative principle:**  
If agent authority is not declared in the registry, it does not exist.
