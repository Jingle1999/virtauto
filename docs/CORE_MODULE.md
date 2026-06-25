# CORE_MODULE.md

**Project:** virtauto.OS
**Module:** `virtauto_core/`
**Status:** Draft
**Strategy:** Variant A – Evolution
**Date:** 2026-06-25

---

# 1. Purpose

`virtauto_core/` is the technical core of virtauto.OS.

It contains the basic runtime components required to evaluate operational states, apply governance contracts, route competing decisions and produce traceable decision outputs.

In simple terms:

> `virtauto_core/` is where virtauto.OS begins to move from website, concept and demonstration into an executable industrial decision runtime.

The module is not yet a production backend. It is the current decision runtime kernel used to test and demonstrate how GEORGE evaluates governed industrial decisions.

---

# 2. Role inside virtauto.OS

Within the overall virtauto.OS architecture, `virtauto_core/` acts as the first executable layer between:

* operational runtime state,
* governance contracts,
* agent-based evaluation,
* decision routing,
* audit trace generation,
* and future API exposure.

It connects the conceptual layer of Decision Intelligence with actual executable software behavior.

The long-term role of `virtauto_core/` is to become the foundation for:

* governed Multi-Agent Systems,
* industrial decision routing,
* contract-based operational control,
* human-in-the-loop decision approval,
* traceable runtime governance,
* and future integration with `virtauto_api/`.

---

# 3. Current Components

The current module contains the following core files:

```text
virtauto_core/
├── base_agent.py
├── decision_contract.py
├── decision_kernel.py
├── george_router.py
├── message_bus.py
└── text_all_contracts.py
```

Each file has a distinct responsibility.

---

# 4. Component Responsibilities

## 4.1 `decision_kernel.py`

`decision_kernel.py` is the current decision evaluation engine.

Its main responsibility is to:

1. load an operational runtime state,
2. load a governance contract,
3. evaluate whether the contract condition is matched,
4. produce a decision such as `ALLOW`, `HOLD` or `BLOCK`,
5. create structured evidence,
6. create a traceable decision object,
7. and write the result into a trace file.

This file currently represents the core logic of the GEORGE Decision Kernel.

### Current role

`decision_kernel.py` turns an operational situation into a governed decision.

Example:

```text
runtime_state + governance_contract
→ evaluation
→ evidence
→ decision trace
```

### Current decision outcomes

The decision kernel currently supports:

* `ALLOW`
* `HOLD`
* `BLOCK`

### Current governance logic

The kernel already supports several industrial governance contract types, including:

* shift change,
* production recovery,
* variant change,
* quality issue,
* machine failure,
* material shortage,
* safety violation,
* idle loss fallback logic.

### Strategic importance

This file is the most important current executable component of virtauto.OS.

It demonstrates that virtauto is not only describing Decision Intelligence, but already implementing the first version of a governed decision runtime.

---

## 4.2 `george_router.py`

`george_router.py` is responsible for routing and prioritizing multiple evaluated decisions.

Its main responsibility is to take several contract evaluation results and determine the final GEORGE decision.

This is important because industrial systems rarely face only one condition at a time.

A line may simultaneously show:

* a safety warning,
* a quality issue,
* a variant change,
* a material condition,
* a production recovery signal.

GEORGE must therefore decide which signal dominates.

### Current role

`george_router.py` transforms multiple decision candidates into one final operational decision.

Example:

```text
[
  ALLOW from production recovery,
  HOLD from quality issue,
  BLOCK from safety violation
]
→ GEORGE final decision: BLOCK
```

### Current prioritization principle

The current principle is:

```text
BLOCK > HOLD > ALLOW
```

In addition, domain priority may be applied where needed.

Example:

```text
Safety > Quality > Production
```

### Strategic importance

This file is where virtauto begins to learn how to prioritize.

It is the first visible step from isolated agent recommendations toward an operational decision layer.

---

## 4.3 `decision_contract.py`

`decision_contract.py` defines the conceptual structure of a decision contract.

A decision contract describes how a specific operational situation should be evaluated.

It is the bridge between:

* governance rules,
* industrial constraints,
* runtime state,
* and executable decision logic.

### Current role

The file supports the idea that industrial decisions should not be hard-coded only inside agents.

Instead, decisions should be governed by explicit contracts.

### Strategic importance

Decision contracts are central to virtauto.OS because they make decision logic:

* visible,
* reviewable,
* versionable,
* auditable,
* reusable,
* and governable.

This is one of the most important architectural ideas behind virtauto.

---

## 4.4 `base_agent.py`

`base_agent.py` defines the basic structure for future agents.

It is intended to provide a common foundation for specialized industrial agents.

Future agents may include:

* Idle Loss Agent,
* Peak Load Agent,
* Quality Agent,
* Material Agent,
* Maintenance Agent,
* Scheduling Agent,
* Operator Review Agent.

### Current role

The current role is foundational.

It prepares the repository for a modular agent architecture without yet forcing a complex production framework.

### Strategic importance

This file supports the long-term transition from a single runtime kernel toward a governed Multi-Agent System.

---

## 4.5 `message_bus.py`

`message_bus.py` represents the first abstraction for message exchange between runtime components.

In a future architecture, a message bus may connect:

* agents,
* decision kernel,
* GEORGE router,
* API endpoints,
* dashboards,
* and audit logging.

### Current role

The file is an early placeholder or lightweight abstraction for internal communication.

### Strategic importance

The message bus concept is important because virtauto.OS should not become a collection of isolated scripts.

It should evolve toward a coordinated runtime environment where components exchange structured events and decisions.

---

## 4.6 `text_all_contracts.py`

`text_all_contracts.py` is currently used to evaluate multiple governance contracts and route the resulting decisions through GEORGE.

It is a practical testing and demonstration script.

### Current role

The script shows how several contracts can be evaluated together and routed into one final decision.

It currently supports the visible runtime snapshot shown on the virtauto.OS status page.

### Strategic importance

This file is important because it demonstrates the end-to-end flow:

```text
runtime state
→ multiple contract evaluations
→ GEORGE prioritization
→ final decision
```

Long term, this functionality should likely move into a formal test file, CLI command or API endpoint.

---

# 5. Current Decision Runtime Flow

The current simplified runtime flow is:

```text
1. Load runtime state
2. Load governance contract
3. Evaluate contract condition
4. Create evidence
5. Create decision trace
6. Repeat for multiple contracts
7. Send all evaluated decisions to GEORGE Router
8. Produce final decision
```

Conceptually:

```text
Operational State
      ↓
Governance Contracts
      ↓
Decision Kernel
      ↓
Evidence + Trace
      ↓
GEORGE Router
      ↓
Final Governed Decision
```

---

# 6. Current Runtime Outputs

The core module currently produces structured decision outputs containing:

* `decision_id`
* `contract_id`
* `runtime_state_id`
* `timestamp`
* `decision`
* `reason`
* `evidence`
* `governance`
* `source_agent`
* prioritization metadata where applicable.

This output is important because it creates the basis for decision traceability.

A decision is not only returned as a result. It is explained through evidence.

---

# 7. Relationship to Governance Contracts

`virtauto_core/` depends on governance contract files stored outside the core module.

Current related location:

```text
virtauto_governance/
```

The core module should not own the contracts.

Instead:

* `virtauto_core/` evaluates contracts,
* `virtauto_governance/` stores contracts,
* `tests/` validates contract behavior,
* `status/` visualizes selected runtime output.

This separation should be preserved.

---

# 8. Relationship to Tests

The current core behavior is tested through files in:

```text
tests/
```

Relevant current test or demonstration files include:

```text
tests/test_all_contracts.py
tests/test_decision_kernel.py
```

The test layer should verify:

* contract evaluation,
* decision output,
* evidence creation,
* trace generation,
* GEORGE prioritization,
* and final decision behavior.

The next important test rule is:

```text
BLOCK > HOLD > ALLOW
```

This rule should be explicitly protected by tests.

---

# 9. Relationship to Website Status Page

The status page currently visualizes selected runtime behavior.

Relevant location:

```text
status/
```

The current website snapshot should gradually move from hard-coded values toward runtime-generated outputs.

Target direction:

```text
virtauto_core/
→ decision output
→ status/latest_decision.json
→ status page visualization
```

This would make the website a visible surface of the runtime system instead of a static demonstration.

---

# 10. Current Maturity Level

Current maturity:

```text
Level 1: Executable Runtime Prototype
```

The module is beyond pure concept or documentation.

It already contains executable decision logic, routing logic and trace generation.

However, it is not yet a production-grade runtime.

### Current strengths

* clear emerging runtime kernel,
* working decision evaluation,
* multiple governance contracts,
* GEORGE prioritization,
* audit trace direction,
* visible website integration,
* testable Python components.

### Current limitations

* mixed prototype and production responsibilities,
* some naming inconsistencies,
* trace format not yet fully standardized,
* no stable API layer yet,
* no persistent database,
* no formal package structure,
* no Docker runtime yet,
* no CI enforcement for core behavior yet.

---

# 11. Target Maturity

Target maturity for the next phase:

```text
Level 2: Stabilized Local Decision Runtime
```

At this level, the core module should provide:

* stable contract evaluation,
* standardized trace format,
* deterministic GEORGE routing,
* tests for all supported contracts,
* clean module boundaries,
* structured outputs for website and API,
* and basic documentation for each core component.

Only after this level is reached should the project move aggressively into Docker, MQTT or external API deployment.

---

# 12. Near-Term Development Priorities

The next technical priorities for `virtauto_core/` are:

## Priority 1 — Stabilize Decision Output

Define one canonical decision output format.

All decisions should consistently include:

```text
decision_id
timestamp
contract_id
decision
reason
evidence
governance
source_agent
priority_metadata
```

## Priority 2 — Standardize Trace Format

There should be one trace format and one preferred trace location.

Recommended direction:

```text
decision_traces/george_trace.jsonl
```

or, if used for website output:

```text
status/latest_decision.json
```

The distinction between internal traces and public website status should remain clear.

## Priority 3 — Protect GEORGE Prioritization with Tests

Add or stabilize tests that ensure:

```text
BLOCK > HOLD > ALLOW
```

and:

```text
Safety > Quality > Production
```

where domain priority is relevant.

## Priority 4 — Separate Demo Scripts from Core Runtime

`text_all_contracts.py` should eventually move out of `virtauto_core/` or be renamed.

Possible future locations:

```text
tests/test_all_contracts.py
```

or:

```text
tools/evaluate_all_contracts.py
```

or:

```text
virtauto_core/runtime_runner.py
```

The decision depends on whether it becomes a test, tool or production runtime entry point.

## Priority 5 — Connect Core Output to Website Snapshot

The website should not permanently rely on hard-coded runtime values.

Target:

```text
python tests/test_all_contracts.py
→ writes status/latest_decision.json
→ status/index.html and status/index-de.html read it
```

## Priority 6 — Prepare Minimal API Interface

Only after the core output is stable, expose it through `virtauto_api/`.

Initial API endpoints may be:

```text
GET /health
GET /latest-decision
GET /contracts
```

---

# 13. Design Rules for Future Core Development

The following rules should guide future changes to `virtauto_core/`.

## Rule 1 — Core must remain small

`virtauto_core/` should contain runtime logic, not website code, not documentation and not experimental notebooks.

## Rule 2 — Governance belongs outside the core

Contracts belong in:

```text
virtauto_governance/
```

The core evaluates contracts but does not own them.

## Rule 3 — Every decision must leave evidence

No decision should be produced without evidence.

## Rule 4 — HOLD is the safe default

If evidence is missing, ambiguous or insufficient, the system should default to `HOLD`.

## Rule 5 — BLOCK must dominate lower-risk decisions

Safety-critical or blocking decisions must override lower-priority recommendations.

## Rule 6 — Tests must protect runtime behavior

Any change to decision evaluation or routing must be covered by tests.

## Rule 7 — Runtime output must remain machine-readable

The output should remain JSON-compatible and suitable for:

* website visualization,
* API exposure,
* audit logging,
* future database storage,
* and external review.

---

# 14. Open Questions

The following architectural questions remain open:

1. Should `text_all_contracts.py` remain in `virtauto_core/` or move to `tests/` or `tools/`?
2. Should `decision_traces/` remain at root level or move under `logs/` or `runtime/`?
3. Should the canonical runtime state live under `virtauto_governance/schemas/` or `schemas/`?
4. Should GEORGE become a class inside `virtauto_core/` or a separate orchestration module?
5. Should the first API expose the latest decision from a static JSON file or execute the decision runtime on demand?
6. Should website status data be generated during CI/CD or updated by a runtime process?

These questions should be resolved step by step, not all at once.

---

# 15. Recommended Next Steps

The recommended next steps are:

1. Commit this document as:

2. Review and align file responsibilities inside `virtauto_core/`.

3. Stabilize `decision_kernel.py`.

4. Stabilize `george_router.py`.

5. Add tests for prioritization.

6. Standardize trace output.

7. Generate `status/latest_decision.json`.

8. Connect website snapshot to runtime output.

9. Only then create the minimal `virtauto_api/`.

---

# 16. Summary

`virtauto_core/` is the current technical heart of virtauto.OS.

It already demonstrates the essential concept:

> Industrial AI should not only recommend actions. It must evaluate operational context, apply governance, prioritize competing signals and produce traceable decisions.

This module is where that idea becomes executable.

The next phase should not add unnecessary complexity.

The next phase should stabilize the core.
