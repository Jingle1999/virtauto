# GEORGE Contract v1 (Frozen)

**Version:** 1.0.1  
**Status:** FROZEN (hard constraints for governance gates)  
**Applies to:** `ops/validate_contract_v1.py` (CI), Guardian checks, and all UI/readers that treat files as authoritative.

---

## 1) Truth Sources (Single Source of Truth)

Authoritative files:

- Canonical system truth: `ops/reports/system_status.json`
- Canonical latest decision: `ops/decisions/latest.json`
- Canonical decision trace stream: `ops/reports/decision_trace.jsonl`

**No other file may be treated as authoritative** by the website, governance gates, or agent runtime.

Backward-compatible / legacy (non-authoritative):

- `ops/status.json` (internal health persistence only)
- `ops/reports/system_status.json` is authoritative; older `status/status.json` or similar are deprecated.

---

## 2) Output Guarantees (Hard)

For every GEORGE run that produces or updates a decision:

1. `ops/decisions/latest.json` **MUST** exist and validate against  
   `ops/contracts/schemas/decision_latest_v1.schema.json`
2. `ops/reports/decision_trace.jsonl` **MUST** contain deterministic records that validate against  
   `ops/contracts/schemas/decision_trace_record_v1.schema.json`
3. `ops/reports/system_status.json` **MUST** exist and validate against  
   `ops/contracts/schemas/system_status_v1.schema.json`

---

## 3) “GEORGE NEVER …” (Hard Rules)

- GEORGE never writes/edits website HTML directly.
- GEORGE never bypasses required governance checks (CI must pass).
- GEORGE never executes actions without writing trace evidence.
- GEORGE never invents alternative truth sources (only the canonical files above).
- GEORGE never writes to unknown/undocumented paths outside `ops/` governed artifacts.

---

## 4) Operating Modes (Contract)

### HUMAN_GUARDED (default)
- GEORGE can **propose** decisions.
- GEORGE cannot **apply** decisions autonomously.
- A “success/applied” state is only legitimate after **human approval via PR merge**.

### NIGHT_SHIFT
- GEORGE may apply decisions **only** if:
  - action is allowlisted,
  - action is reversible,
  - rate limits are respected,
  - stop rules do not trigger.

---

## 5) Action Policy (Allowlist / Denylist)

### Allowlist (explicit)
- `switch_degraded_mode`
- `rollback_to_last_known_good`
- `restart_probe_worker`

### Denylist (patterns)
- `deploy_*` (no autonomous deploys in v1)
- `delete_*` (no destructive actions)
- `exfiltrate_*` (no data exfiltration)
- `*credential*`, `*token*` (no credential/token access)

> **Important:** “Not allowlisted” means “not applicable” in NIGHT_SHIFT.

---

## 6) Status Vocabulary (Allowed Values)

Decision status:
- `pending`
- `success`
- `error`
- `blocked`

System/Agent state:
- `ok`
- `degraded`
- `blocked`
- `unknown`

Autonomy mode:
- `supervised`
- `advisory`
- `enforced`

---

## 7) Gate Compatibility Contract

`ops/decisions/latest.json` MUST contain (at minimum):

- `decision_id` (string)
- `decision_class` (string)
- `authority_source` (string)
- `agent` (string)
- `action` (string)
- `status` (string, from vocabulary)
- `timestamp` (ISO UTC)
- `signals` (object)
- `trace` (object)

---

## 8) Trace Determinism

A valid decision trace must contain these phases **in order** (at least once each):

- `route`
- `guardian_precheck`
- `authority_enforcement`
- `execute_or_blocked`
- `guardian_postcheck`
- `finalize`

Each trace record must include:

- `ts` (ISO UTC)
- `trace_version` (e.g. `v1`)
- `decision_id`
- `actor`
- `phase`
- `result`

---

## 9) Enforcement

- Contract validation runs in CI via `ops/validate_contract_v1.py`.
- Any contract violation is a hard FAIL (merge blocked).

---

## 10) What we still need next (Phase 10 readiness)

To make GEORGE truly **Hard Governing** (not only “proto-governing”), we still need:

1. A runtime-visible **active mode file** (e.g. `ops/george/mode.json`) governed by PR rules.
2. A hard-stop executor boundary (where “apply” can be technically refused, not just recorded).
3. A contract-aware action runner that maps `decision.action` → permitted tools with safe defaults.

This contract is the foundation; the next step is binding execution to it.
