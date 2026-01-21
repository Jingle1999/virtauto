# Phase 9 — Self-Healing (Adaptive Systems v1)

**Scope:** Regression recovery only · PR-only · deterministic · governed

---

## Objective (Non-Negotiable)

**Phase 9 goal (precise):**

When a **known regression** occurs, the system:

1. detects it **deterministically**,
2. selects a **known repair path**,
3. automatically opens a **Pull Request**,
4. runs the relevant checks/tests,
5. **never changes `main` autonomously**,
6. produces complete **decision traces**.

**Explicitly out of scope**
- ❌ No optimization
- ❌ No learning
- ❌ No autonomy escalation
- ✅ Stability and controlled recovery only

---

## Regression Triggers (Final)

Phase 9 supports **exactly three** regression types.

### R1 — Capability Graph Invalid

**Meaning:**  
`governance/resilience/capability_graph.json` is syntactically or semantically invalid  
(e.g. missing `primary`, invalid references, cycles, unknown capabilities).

**Detection**
- JSON schema validation
- Reference validation against `ops/capability_profiles.json`
- Determinism rule: **exactly one `primary`**

---

### R2 — Status Validation Fails

**Meaning:**  
`system_status.json` violates truth rules (inconsistency, missing fields, invalid values).

**Detection**
- Validator: `ops/validate_status.py`
- Trigger conditions:
  - Exit code ≠ 0
  - Required fields missing
  - Autonomy score inconsistent

---

### R3 — Mandatory Artifact Missing

**Meaning:**  
A required artifact was not produced after a workflow run.

**Mandatory artifacts (fixed)**
- `decision_trace.jsonl`
- `gate_result.json`
- `system_status.json`
- `latest.json`

---

## Governance Principle (Golden Rule)

**Self-Healing never performs direct changes.**  
**Self-Healing proposes changes.**

➡️ **PR-only. Always.**  
➡️ **No auto-merge.**  
➡️ Human review is part of the design.

---

## Repository Structure

