GEORGE Contract v1 (Frozen)
Version: 1.0.2
Status: FROZEN (hard constraints for governance gates)
Applies to: ops/validate_contract_v1.py (CI), Guardian checks, and all UI/readers that treat files as authoritative.


1) Truth Sources (Single Source of Truth)

Authoritative files (SSOT):

Canonical system truth:
ops/reports/system_status.json

Canonical latest decision:
ops/decisions/latest.json

Canonical decision trace stream:
ops/reports/decision_trace.jsonl

No other file may be treated as authoritative by:
- the website
- governance gates
- any agent runtime
- dashboards
- workflows

Legacy / deprecated (non-authoritative):

ops/status.json (deprecated pointer only; MUST NOT contain authoritative state)
status/status.json or similar legacy artifacts are deprecated and MUST NOT be used.


2) Output Guarantees (Hard)

For every GEORGE run that produces or updates a decision:

ops/decisions/latest.json MUST:
- exist
- validate against ops/contracts/schemas/decision_latest_v1.schema.json

ops/reports/decision_trace.jsonl MUST:
- contain deterministic records
- validate against ops/contracts/schemas/decision_trace_record_v1.schema.json

ops/reports/system_status.json MUST:
- exist
- validate against ops/contracts/schemas/system_status_v1.schema.json


3) “GEORGE NEVER …” (Hard Rules)

GEORGE never writes or edits website HTML directly.

GEORGE never bypasses required governance checks.
(CI must pass; no administrative override of required checks.)

GEORGE never executes actions without writing trace evidence.

GEORGE never invents alternative truth sources.
(Only the canonical files defined in Section 1 are valid.)

GEORGE never writes to unknown or undocumented paths outside governed ops/ artifacts.

GEORGE never elevates autonomy level without a governance event.


4) Operating Modes (Contract)

HUMAN_GUARDED (default)

- GEORGE can propose decisions.
- GEORGE cannot apply decisions autonomously.
- A “success/applied” state is legitimate only after PR merge.


NIGHT_SHIFT

GEORGE may apply decisions only if:

- action is explicitly allowlisted
- action is reversible
- rate limits are respected
- stop rules do not trigger
- trace is written before execution
- system_status.json is updated deterministically


5) Action Policy (Allowlist / Denylist)

Allowlist (explicit)

- switch_degraded_mode
- rollback_to_last_known_good
- restart_probe_worker


Denylist (patterns)

- deploy_* (no autonomous deploys in v1)
- delete_* (no destructive actions)
- exfiltrate_* (no data exfiltration)
- *credential*
- *token*

Important:
"Not allowlisted" means "not applicable" in NIGHT_SHIFT.
Absence from allowlist = automatic block.


6) Status Vocabulary (Allowed Values)

Decision status:

- pending
- success
- error
- blocked


System / Agent state:

- ok
- degraded
- blocked
- unknown


Autonomy mode:

- supervised
- advisory
- enforced


7) Gate Compatibility Contract

ops/decisions/latest.json MUST contain (at minimum):

- decision_id (string)
- decision_class (string)
- authority_source (string)
- agent (string)
- action (string)
- status (string, from vocabulary)
- timestamp (ISO UTC)
- signals (object)
- trace (object)


8) Trace Determinism

A valid decision trace MUST contain these phases in order
(at least once each):

- route
- guardian_precheck
- authority_enforcement
- execute_or_blocked
- guardian_postcheck
- finalize

Each trace record MUST include:

- ts (ISO UTC)
- trace_version (e.g. v1)
- decision_id
- actor
- phase
- result


9) Enforcement

Contract validation runs in CI via:

ops/validate_contract_v1.py

Any contract violation is a hard FAIL.
Merge is blocked.

There are no soft warnings for contract violations.


10) Phase 10 Readiness (Next Hardening Steps)

To move from proto-governing to hard-governing execution, the following must exist:

- A runtime-visible active mode file
  (e.g. ops/george/mode.json), governed via PR

- A hard execution boundary
  (execution can be technically refused, not only logged)

- A contract-aware action runner
  mapping decision.action → permitted tools
  with safe defaults and deny-by-default behavior

This contract defines the normative boundary.
Execution must bind to it.
