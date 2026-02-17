# Decision Trace (PR): Add Required Fields to agents/registry.yaml

## Decision / Intent
Bring agent registry into compliance with CI-required fields.
Goal: Ensure every agent has `autonomy_mode` and `state`.

## Authority
- Class: Governance / Agent Registry
- Level: Supervised
- Escalation: Human approval required for merge

## Scope (files/modules touched)
- agents/registry.yaml

## Expected outcome
- Consistency Agent no longer fails on missing `autonomy_mode` / `state`.
- Registry becomes a stable contract for further governance checks.
