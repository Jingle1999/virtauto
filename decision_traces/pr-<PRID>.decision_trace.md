# PR Decision Trace — pr-<PRID>

## Intent
Add Stage 1.1 bounded advisory energy optimization decision classes for BIW doorline:
- energy_output_stability_advisory (Door Model 2)
- energy_peak_mitigation_advisory (Door Model 3)

## Scope / Changes
- Add contracts:
  - governance/contracts/energy-output-stability-advisory-v1.md
  - governance/contracts/energy-peak-mitigation-advisory-v1.md
- Add ruleset:
  - governance/rulesets/biw-door-energy-v1.json
- Add demo examples:
  - ops/examples/*.json
- Minimal industrymodel.html update (Stage 1.1 + artifacts)

## Authority
Advisory-only; no autonomous execution on shopfloor.
All recommendations remain within approved envelopes and are BLOCKed under quality/stability guards.

## Risks & Mitigations
- Risk: unclear peak target value → mitigated by conservative defaults (peak_limit_kw=0) and explicit “not configured” note.
- Risk: drift/instability could cause bad advice → mitigated by hard BLOCK guardrails.

## Outcome
Governed artifacts added; validator-compatible; PR includes PR-scoped decision trace (this file).
