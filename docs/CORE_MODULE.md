# CORE_MODULE.md

**Project:** virtauto.OS  
**Module:** `virtauto_core/`  
**Status:** Draft  
**Strategy:** Variant A – Evolution  
**Date:** 2026-06-30

---

# 1. Purpose

`virtauto_core/` is the technical core of virtauto.OS.

Its current purpose is to provide the first executable decision kernel for governed industrial decisions.

In simple terms:

> `virtauto_core/` is where virtauto.OS begins to move from website, concept and demonstration into an executable industrial decision runtime.

The module is not yet a production backend. It is currently a small but important runtime kernel that evaluates operational state against governance contracts and produces traceable decision outputs.

The current module should remain intentionally small.

It should stabilize the decision kernel first before additional runtime, API, Docker, MQTT or agent infrastructure is added.

---

# 2. Role inside virtauto.OS

Within the overall virtauto.OS architecture, `virtauto_core/` acts as the first executable layer between:

* operational runtime state,
* governance contracts,
* decision evaluation,
* evidence generation,
* decision trace generation,
* and future API exposure.

It connects the conceptual layer of Decision Intelligence with actual executable software behavior.

The long-term role of `virtauto_core/` is to become the foundation for:

* governed Multi-Agent Systems,
* industrial decision routing,
* contract-based operational control,
* human-in-the-loop decision approval,
* traceable runtime governance,
* decision snapshots,
* and future integration with `virtauto_api/`.

However, this long-term role should not be confused with the current repository state.

The current verified executable component inside `virtauto_core/` is:

```text
virtauto_core/
└── decision_kernel.py

-----------------------------------------------------------------------------------------------------------------------------------
Related runtime and governance components currently exist outside virtauto_core/, especially in:
ops/
ops/runtime/
ops/reports/
ops/decisions/
virtauto_governance/
tests/
status/
-----------------------------------------------------------------------------------------------------------------------------------
3. Current Components

Based on the currently verified repository state, virtauto_core/ contains:

virtauto_core/
└── decision_kernel.py

The following files or concepts are relevant to the runtime architecture, but should not be described as current files inside virtauto_core/ unless they are actually moved or created there:

ops/george_orchestrator_v2.py
ops/contract_enforcer.py
ops/guardian_agent.py
ops/runtime/decision_runtime_v1.py
tests/test_all_contracts.py
status/latest_decision.json
decision_traces/
virtauto_governance/contracts/
virtauto_governance/schemas/

This distinction is important.

virtauto_core/ should describe the current core module, not the entire runtime ecosystem.

4. Component Responsibilities
4.1 decision_kernel.py

decision_kernel.py is the current decision evaluation engine inside virtauto_core/.

Its main responsibility is to:

load an operational runtime state,
load a governance contract,
evaluate whether the contract condition is matched,
produce a decision such as ALLOW, HOLD or BLOCK,
create structured evidence,
create a traceable decision object,
and write the result into a trace file.

This file currently represents the core executable logic of the GEORGE Decision Kernel.

Current role

decision_kernel.py turns an operational situation into a governed decision.

Example:

runtime_state + governance_contract
→ evaluation
→ evidence
→ decision trace
Current decision outcomes

The decision kernel currently supports:

ALLOW
HOLD
BLOCK
Current governance logic

The kernel currently supports several industrial governance contract types, including:

shift change,
production recovery,
variant change,
quality issue,
machine failure,
idle loss fallback logic.

The broader repository also contains additional governance concepts and contracts, such as safety violation and material-related logic, but these should be documented according to their actual implemented location.

Strategic importance

This file is the most important current executable component of virtauto_core/.

It demonstrates that virtauto is not only describing Decision Intelligence, but already implementing the first version of a governed decision runtime.

4.2 Related Runtime Component: ops/george_orchestrator_v2.py

ops/george_orchestrator_v2.py is not currently part of virtauto_core/, but it is relevant to the broader runtime architecture.

It handles energy scan completion events and transforms them into structured decision artifacts.

Its current responsibilities include:

reading event data,
evaluating saving potential, confidence and traffic status,
producing a verdict such as BLOCK or RECOMMEND,
defining an action such as ESCALATE, REQUEST_BASELINE, SHAPE_LOAD or KEEP,
writing a decision trace,
and saving the latest decision output.

Current output locations include:

ops/reports/decision_traces.jsonl
ops/decisions/latest.json
Strategic importance

This component shows how virtauto.OS can transform operational events into decision artifacts.

It is especially relevant for the future connection between runtime events, GEORGE decision logic and the website/API layer.

4.3 Related Runtime Component: ops/contract_enforcer.py

ops/contract_enforcer.py is not currently part of virtauto_core/, but it is an important runtime governance component.

Its purpose is to make GEORGE contracts actionable at runtime without directly executing actions.

It evaluates whether an action may be proposed or applied.

Its current responsibilities include:

loading the GEORGE contract,
validating the contract against its schema,
resolving GEORGE mode,
checking allowlist and denylist rules,
returning a ContractDecision,
distinguishing between propose_ok and apply_ok.
Strategic importance

This component reinforces an important virtauto.OS principle:

The system may recommend, propose and trace decisions before it is allowed to execute them.

This supports the current advisory and human-in-the-loop operating model.

4.4 Related Governance Component: ops/guardian_agent.py

ops/guardian_agent.py is not currently part of virtauto_core/, but it is relevant to runtime governance and policy enforcement.

It is a deterministic Guardian/Authority Agent.

Its current responsibilities include:

loading a policy file,
checking required truth files,
checking whether the status page references the required truth path,
scanning configured paths for messaging controls,
producing findings,
writing governance outputs,
writing trace events,
returning a hard governance verdict.

Current output locations include:

ops/reports/governance_outputs.json
ops/reports/guardian_trace.jsonl
ops/agent_activity.jsonl
Strategic importance

This component supports the governance side of virtauto.OS.

It helps ensure that the runtime and website do not drift away from defined truth sources and policy constraints.

4.5 Related Runtime Component: ops/runtime/decision_runtime_v1.py

ops/runtime/decision_runtime_v1.py is not currently part of virtauto_core/, but it is relevant to the future decision runtime.

It represents a more structured decision runtime flow for the energy peak mitigation use case.

Its current responsibilities include:

loading an input event,
building a runtime context,
creating a decision contract,
resolving authority,
evaluating a gate,
building a decision result,
writing traces,
writing latest decision artifacts.

Current output locations include:

ops/reports/decision_trace.jsonl
ops/reports/decision_trace.json
ops/decisions/latest.json
ops/decisions/gate_result.json
ops/decisions/contracts/
ops/decisions/results/
Strategic importance

This file already points toward a more complete decision runtime architecture.

It should be reviewed before deciding whether future runtime logic belongs in:

virtauto_core/

or:

ops/runtime/

The decision should be made explicitly, not by accidental duplication.

4.6 Testing and Demonstration Layer

The current repository also contains test and demonstration logic outside virtauto_core/.

Relevant known location:

tests/

Relevant known file:

tests/test_all_contracts.py

This layer is important because it can verify the end-to-end behavior:

runtime state
→ governance contracts
→ decision kernel
→ multiple decisions
→ final decision
→ trace/output

The test layer should become the preferred place for validating behavior.

Runtime demonstration scripts should not permanently live inside virtauto_core/ unless they are formal runtime entry points.

5. Current Decision Runtime Flow

The currently verified simplified flow around virtauto_core/decision_kernel.py is:

1. Load runtime state
2. Load governance contract
3. Evaluate contract condition
4. Create evidence
5. Create decision trace
6. Write trace output

The broader runtime ecosystem already points toward a larger flow:

Operational State / Event
      ↓
Governance Contracts
      ↓
Decision Kernel / Runtime Evaluation
      ↓
Evidence + Trace
      ↓
Decision Output
      ↓
Website / API / Reports

For multiple competing decisions, the intended GEORGE routing principle is:

Multiple evaluated decisions
      ↓
Prioritization
      ↓
Final governed decision

The prioritization rule to protect is:

BLOCK > HOLD > ALLOW

Where domain priority is relevant, the intended domain rule is:

Safety > Quality > Production
6. Current Runtime Outputs

The current decision kernel produces structured decision outputs containing:

decision_id
contract_id
runtime_state_id
timestamp
decision
runtime_state
reason
evidence
governance

Related runtime components also produce outputs such as:

verdict
action
confidence
constraints
gate_verdict
recommendation
trace_id
artifacts

This means the repository already contains several overlapping output formats.

That is useful for experimentation, but it must now be stabilized.

The next target should be one canonical decision output format.

A decision should not only say what the system decided.

It should also explain:

why the decision was made,
which evidence was used,
which contract or policy applied,
what execution mode was allowed,
whether human approval is required,
and what decision environment existed at decision time.
7. Relationship to Governance Contracts

virtauto_core/ depends on governance contract files stored outside the core module.

Current related location:

virtauto_governance/

The core module should not own the contracts.

Instead:

virtauto_core/ evaluates contracts,
virtauto_governance/ stores contracts and schemas,
ops/ contains broader runtime and governance tooling,
tests/ validates contract behavior,
status/ visualizes selected runtime output.

This separation should be preserved.

A clean separation is important because governance contracts must remain:

visible,
reviewable,
versionable,
auditable,
reusable,
and governable.
8. Relationship to Tests

The current core behavior should be tested through files in:

tests/

Known relevant test or demonstration file:

tests/test_all_contracts.py

The test layer should verify:

contract evaluation,
decision output,
evidence creation,
trace generation,
prioritization,
and final decision behavior.

The most important next test rule is:

BLOCK > HOLD > ALLOW

This rule should be explicitly protected by tests.

A second important test rule is:

Safety > Quality > Production

where domain priority is relevant.

Tests should also protect the safe default principle:

missing evidence → HOLD
ambiguous evidence → HOLD
unknown action → no apply
9. Relationship to Website Status Page

The status page currently visualizes selected runtime behavior.

Relevant location:

status/

The current website snapshot should gradually move from hard-coded values toward runtime-generated outputs.

Target direction:

runtime evaluation
→ latest decision artifact
→ status/latest_decision.json
→ status page visualization

This would make the website a visible surface of the runtime system instead of a static demonstration.

However, the website must not be broken during this transition.

Therefore:

no HTML files should be moved until dependencies are checked,
status pages should remain stable,
generated data files should be introduced carefully,
the English and German status pages should remain harmonized.
10. Current Maturity Level

Current maturity:

Level 1: Executable Runtime Prototype

The module is beyond pure concept or documentation.

It already contains executable decision logic and trace generation.

The broader repository also contains related runtime, governance and orchestration components.

However, it is not yet a production-grade runtime.

Current strengths
clear emerging runtime kernel,
working decision evaluation,
governance contract direction,
audit trace direction,
website integration,
testable Python components,
early runtime artifacts in ops/,
early governance enforcement through contract_enforcer.py,
deterministic policy checking through guardian_agent.py.
Current limitations
virtauto_core/ is smaller than previously documented,
some runtime responsibilities are split across virtauto_core/, ops/ and ops/runtime/,
several output and trace formats exist in parallel,
trace format is not yet fully standardized,
decision snapshot format is not yet defined,
no stable API layer yet,
no persistent database,
no formal package structure,
no Docker runtime yet,
no CI enforcement for core behavior yet.
11. Target Maturity

Target maturity for the next phase:

Level 2: Stabilized Local Decision Runtime

At this level, the system should provide:

stable contract evaluation,
one canonical decision output format,
one canonical trace format,
one decision snapshot format,
deterministic prioritization,
tests for all supported contracts,
tests for prioritization,
clean module boundaries,
structured outputs for website and API,
and basic documentation for each core/runtime component.

Only after this level is reached should the project move aggressively into Docker, MQTT or external API deployment.

The next goal is not maximum infrastructure.

The next goal is a trustworthy local decision runtime.

12. Near-Term Development Priorities

The next technical priorities are:

Priority 1 — Correct the current module boundary

The documentation must reflect the actual repository state.

Current verified virtauto_core/ content:

virtauto_core/
└── decision_kernel.py

Related runtime components should be documented as related components, not as files inside virtauto_core/.

Priority 2 — Stabilize Decision Output

Define one canonical decision output format.

All decisions should consistently include:

decision_id
timestamp
contract_id
decision
reason
evidence
governance
source_agent
priority_metadata
trace_id
snapshot_id
Priority 3 — Add Decision Snapshot

A decision trace alone is not enough for full Decision Intelligence.

A trace records what happened.

A decision snapshot should capture the state of the decision environment at the moment the decision was made.

A decision snapshot should include:

snapshot_id
decision_id
timestamp
runtime_state
input_data_reference
contract_versions
policy_versions
model_versions
constraints
objectives
context
evidence
decision_result
execution_mode
human_approval_state

The purpose is reproducibility.

The system should eventually be able to explain not only:

What did GEORGE decide?

but also:

Under which exact conditions was that decision made?
Priority 4 — Standardize Trace Format

There should be one preferred trace format and one preferred internal trace location.

Candidate direction:

decision_traces/george_trace.jsonl

or:

ops/reports/decision_trace.jsonl

This needs to be decided explicitly.

The distinction between internal traces and public website status should remain clear.

Priority 5 — Protect Prioritization with Tests

Add or stabilize tests that ensure:

BLOCK > HOLD > ALLOW

and:

Safety > Quality > Production

where domain priority is relevant.

Priority 6 — Connect Runtime Output to Website Snapshot

The website should not permanently rely on hard-coded runtime values.

Target:

runtime/test run
→ writes latest decision artifact
→ writes latest decision snapshot
→ status page reads generated output

Possible public output:

status/latest_decision.json
status/latest_snapshot.json
Priority 7 — Prepare Minimal API Interface

Only after the core output and snapshot format are stable, expose them through virtauto_api/.

Initial API endpoints may be:

GET /health
GET /latest-decision
GET /latest-snapshot
GET /contracts
13. Design Rules for Future Core Development

The following rules should guide future changes to virtauto_core/.

Rule 1 — Core must remain small

virtauto_core/ should contain runtime logic, not website code, not documentation and not experimental notebooks.

Rule 2 — Governance belongs outside the core

Contracts belong in:

virtauto_governance/

The core evaluates contracts but does not own them.

Rule 3 — Every decision must leave evidence

No decision should be produced without evidence.

Rule 4 — HOLD is the safe default

If evidence is missing, ambiguous or insufficient, the system should default to HOLD.

Rule 5 — BLOCK must dominate lower-risk decisions

Safety-critical or blocking decisions must override lower-priority recommendations.

Rule 6 — Tests must protect runtime behavior

Any change to decision evaluation or routing must be covered by tests.

Rule 7 — Runtime output must remain machine-readable

The output should remain JSON-compatible and suitable for:

website visualization,
API exposure,
audit logging,
future database storage,
and external review.
Rule 8 — A trace is not enough

A decision trace records the decision path.

A decision snapshot captures the decision environment.

Both are needed.

Rule 9 — Reproducibility requires versioning

The system should increasingly version:

data,
contracts,
policies,
models,
objectives,
constraints,
and runtime context.

Without this, replaying a decision may produce a different result after the environment changes.

Rule 10 — No infrastructure before core stability

Docker, MQTT, databases and external APIs should follow core stabilization.

They should not hide unresolved runtime ambiguity.

14. Open Questions

The following architectural questions remain open:

Should broader runtime logic move from ops/runtime/ into virtauto_core/, or should ops/runtime/ remain the runtime execution area?
Should GEORGE routing become part of virtauto_core/ as a dedicated class, or remain in ops/ until the architecture stabilizes?
Should the canonical trace location be decision_traces/ or ops/reports/?
Should the public website consume status/latest_decision.json, status/latest_snapshot.json, or both?
Should decision snapshots be generated during tests, during CI/CD, or during an explicit runtime command?
Should the first API expose static generated artifacts or execute the decision runtime on demand?
Should contracts remain only in virtauto_governance/, or should selected examples remain under ops/contracts/ for backward compatibility?
Which component should own the canonical decision schema?
Which component should own the canonical decision snapshot schema?
How should existing overlapping trace files be consolidated without breaking current website behavior?

These questions should be resolved step by step, not all at once.

15. Recommended Next Steps

The recommended next steps are:

Commit this corrected document as:
docs/CORE_MODULE.md
Create a dedicated decision snapshot document:
docs/DECISION_SNAPSHOT.md
Define the canonical decision output format.
Define the canonical decision snapshot format.
Review virtauto_core/decision_kernel.py against the canonical format.
Review related runtime files:
ops/george_orchestrator_v2.py
ops/contract_enforcer.py
ops/guardian_agent.py
ops/runtime/decision_runtime_v1.py
Decide whether GEORGE prioritization belongs in virtauto_core/ or remains in ops/ for now.
Add or stabilize tests for:
BLOCK > HOLD > ALLOW
Add or stabilize tests for:
Safety > Quality > Production
Standardize trace output.
Generate a latest decision artifact.
Generate a latest decision snapshot artifact.
Connect the website snapshot to generated runtime output.
Harmonize English and German status pages.
Only then create the minimal virtauto_api/.
Only after that prepare Docker and MQTT.

16. Summary

virtauto_core/ is the current technical heart of virtauto.OS, but it is smaller than previously documented.

Its verified current executable component is:

virtauto_core/decision_kernel.py

The broader repository already contains related runtime, governance and orchestration components in ops/, ops/runtime/, virtauto_governance/, tests/ and status/.

The next phase should not add unnecessary infrastructure.

The next phase should stabilize the decision runtime.

The most important architectural update is this:

A Decision Trace is necessary, but not sufficient.
Decision Intelligence also needs a Decision Snapshot: a versioned capture of the decision environment at the moment a decision is made.

Industrial AI should not only recommend actions.

It must evaluate operational context, apply governance, prioritize competing signals, capture the decision environment and produce traceable, reproducible decisions.

This is the next step for virtauto.OS.
