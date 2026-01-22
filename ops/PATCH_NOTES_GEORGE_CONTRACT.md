# virtauto – GEORGE Contract: next step to *proto-governing*

This patch makes the existing **GEORGE Contract v1** actionable at runtime by adding **contract enforcement** to `ops/george_orchestrator_v2.py`.

## What changed

### 1) New: `ops/contract_enforcer.py`
- Loads + (optionally) validates `ops/contracts/george_contract_v1.json` against `ops/contracts/schemas/george_contract_v1.schema.json`
- Resolves the active autonomy mode via:
  1. `GEORGE_MODE` env var
  2. `ops/george_mode.json`
  3. `contract.default_mode`
- Evaluates actions against:
  - denylist (highest priority)
  - allowlist (required for APPLY)
  - mode capabilities (`can_apply`, `can_propose`, `requires_human_approval`)
- Produces a deterministic decision object used by the orchestrator.

### 2) Updated: `ops/george_orchestrator_v2.py`
- Ensures every trace record includes a `decision_id` (schema compliance).
- Adds a `contract_check` step before execution:
  - If contract disallows APPLY: decision is materialized + traced but execution is blocked (proposal-only behavior).

### 3) New: `ops/george_mode.json`
- Governance-controlled place to set the current mode (default `HUMAN_GUARDED`).

## Why this matters
- Before: contract existed, but nothing *had* to obey it.
- Now: the orchestrator cannot execute side effects unless the contract allows it.
- This moves Phase 5 (GEORGE Contract) from "text only" toward "binding".

## How to apply
Copy these files into your repo (1:1 replacement / addition):

- `ops/contract_enforcer.py` (new)
- `ops/george_orchestrator_v2.py` (replace)
- `ops/george_mode.json` (new)
- `PATCH_NOTES_GEORGE_CONTRACT.md` (optional)

Then run:
- `python ops/validate_contract_v1.py`
- `python ops/validate_decision_trace.py`
