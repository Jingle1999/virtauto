## Decision / Intent
Update `self_healing/heal.py` to improve Phase 9 audit visibility and deterministic self-healing outputs.

## Authority
System governance — Phase 9 implementation.

## Scope (files/modules touched)
- self_healing/heal.py

## Expected outcome
- PR checks become deterministic and audit-visible for Phase 9.
- No direct writes to main; PR-only workflow unchanged.
# Decision Trace

## Decision / Intent
Introduce an explicit, deterministic detector for regression type R1
(Capability Graph Invalid) as part of Phase 9: Self-Healing.

## Authority
System governance – Phase 9 implementation.

## Scope
Files affected:
- self_healing/detectors/detect_capability_regression.py

## Expected Outcome
Self-Healing-Workflow automation: R1 regressions become explicitly detectable, audit-visible, and
machine-verifiable without changing system autonomy.
