# Decision Trace — AEO Stage 1 (Bounded Decision Space)

This document explains how **decision traces** work in virtauto and which
checks are enforced before a production-relevant decision is allowed,
held, or blocked.

It complements the machine-readable trace stored in:
ops/reports/decision_trace.jsonl


This file is **documentation**, not evidence.
The JSONL trace is the single source of truth.

---

## 1. Purpose of a Decision Trace

A decision trace ensures that **no industrial decision is executed without
explicit authority, evidence, and governance**.

In AEO Stage 1, the trace must answer one question unambiguously:

> **Why was this decision ALLOWED, HELD, or BLOCKED?**

The trace is:
- decision-first (not data-first)
- audit-first (not KPI-first)
- block-capable (not demo-capable)
- append-only (never rewritten)

---

## 2. Trace Format (Record-Based, JSONL)

Each line in `decision_trace.jsonl` represents **one step** in a governed
decision flow.

Minimal required fields per record:

| Field | Meaning |
|------|--------|
| `ts` | ISO-8601 timestamp |
| `trace_version` | Trace schema version |
| `decision_id` | Stable decision identifier |
| `actor` | System actor responsible for the step |
| `phase` | Decision phase |
| `result` | Outcome or evaluation result |

---

## 3. Decision Phases (Stage 1)

A valid decision trace follows a deterministic sequence.
Not all phases must appear, but **BLOCK must be explicit**.

### 3.1 Route
**Actor:** Orchestrator  
**Purpose:**  
Defines *what* decision is about to be evaluated.

Example:
- decision class
- domain
- contract reference
- intent

---

### 3.2 Guardian Precheck
**Actor:** Guardian  
**Purpose:**  
Validates structural correctness before authority is evaluated.

Typical checks:
- Evidence chain present
- Required inputs provided
- Contract version resolved

Failure here leads to **BLOCK**.

---

### 3.3 Authority Enforcement
**Actor:** Orchestrator / Authority Engine  
**Purpose:**  
Ensures the decision has a legitimate authority path.

Checks include:
- Required authority role present
- Policy version applicable
- Non-negotiables respected

If authority is missing → **BLOCK**.

---

### 3.4 Execute (Deterministic Checks)
**Actor:** Edge / Deterministic Evaluator  
**Purpose:**  
Runs **non-optimizing**, deterministic checks only.

Examples:
- Geometry within tolerance
- Surface quality OK
- Gap & flush within limits

No learning. No prediction. No optimization.

---

### 3.5 Guardian Postcheck
**Actor:** Guardian  
**Purpose:**  
Evaluates whether the execution result may transition system state.

Outputs:
- `ALLOW`
- `HOLD`
- `BLOCK`

Every BLOCK must include:
- explicit reason
- violated rule or missing evidence

---

### 3.6 Finalize
**Actor:** Orchestrator  
**Purpose:**  
Commits the final verdict and references the audit record.

This is the **only phase** allowed to finalize system state.

---

## 4. BLOCK Is a First-Class Outcome

BLOCK is **not a failure**.

BLOCK means:
- the system protected itself
- authority or evidence was insufficient
- escalation is required

A successful AEO system **must** be able to block itself.

---

## 5. Validation Rules (What CI Enforces)

The following checks are enforced by CI:

### Mandatory
- Decision trace file exists
- File is non-empty
- Each record contains:
  - `ts`
  - `trace_version`
  - `decision_id`
  - `actor`
  - `phase`
  - `result`

### Structural
- JSONL format
- One JSON object per line
- Append-only semantics

### Intentional Non-Checks (by design)
- No enforcement of phase order
- No enforcement of specific actors
- No requirement for ALLOW outcome

This keeps Stage 1 **strict but non-brittle**.

---

## 6. Relationship to Decision Contracts

The decision trace is the **runtime realization** of a decision contract.

Example:
- Contract: `pp-door-release-v1.md`
- Trace: concrete execution of that contract
- CI validates presence, not correctness of business logic

Correctness is a **governance responsibility**, not a validator responsibility.

---

## 7. Summary

- The decision trace is mandatory
- BLOCK is a valid and desired outcome
- Governance is active even when nothing breaks
- Industry credibility comes from traceability, not autonomy claims

> If the system cannot explain *why it stopped*, it is not autonomous — it is reckless.
