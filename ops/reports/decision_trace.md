# Decision Trace – Normative Specification

## Purpose

The decision trace is the authoritative audit record for all decisions taken
by virtauto’s governance system.

**Rule: No decision without trace.**

This file defines how decisions are logged, evaluated, blocked, and explained.
It serves as the normative reference for:
- industrymodel.html
- Guardian enforcement
- Authority validation
- Audit and compliance review

---

## File Location
virtauto/ops/reports/decision_trace.jsonl


Format: **JSON Lines (one object per line)**

---

## Core Principles

1. **One decision = one decision_id**
2. A decision may span multiple phases
3. A decision always ends with exactly one verdict
4. Missing or incomplete evidence MUST lead to BLOCK
5. No human or system override without governed approval path

---

## Mandatory Phases

Each decision MUST follow this logical order (phases may be skipped if not applicable):

1. `route` – classify and route the decision
2. `execute` – collect evidence and run checks
3. `guardian_precheck` – apply safety and fail-safe policies
4. `authority_enforcement` – verify decision authority
5. `finalize` – emit final verdict (ALLOW | BLOCK | ESCALATE)

---

## Block Semantics

A decision is BLOCKED if any of the following is true:
- required evidence is missing
- a guardian policy fails
- required authority is not present
- system is in PR_ONLY governance mode and no approval exists

**Fail-safe default: BLOCK**

---

## Industry Model Alignment

This structure mirrors the decision logic shown in `industrymodel.html`.

The website itself operates under the same rules it demonstrates:
- no silent actions
- no direct writes
- no untraceable decisions

This makes virtauto a living reference system for governed industrial autonomy.
