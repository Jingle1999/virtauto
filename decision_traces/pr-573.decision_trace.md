# Decision Trace — PR-573 — industrymodel.html update

- **PR:** #573
- **Branch:** Jingle1999-patch-996907
- **Change type:** Documentation / Spec update (normative UI spec)
- **Scope:** `industrymodel.html`
- **Risk level:** Low (content + structure only, no runtime logic change)
- **Decision class affected:** `industrymodel_spec_v1` (documentation artifact)
- **Governance posture:** PR-only, audit-first, no silent claims

## 1) Intent
Integrate the energy optimization use-case into `industrymodel.html` so that it is consistent with the AEO Stage 1 narrative and does not feel detached.
The page must remain a **normative proof object** and only claim capabilities backed by governed artifacts.

## 2) What changed
- Updated `industrymodel.html` to position **Stage 1.1 — Energy Optimization (bounded advisory)** coherently inside the spec.
- Ensured the Decision Space table references the additional decision classes:
  - `energy_output_stability_advisory` (Door Model 2)
  - `energy_peak_mitigation_advisory` (Door Model 3)
- Kept the governing baseline intact: `pp_door_release` remains the gate-blocking decision class.

## 3) Constraints & non-negotiables checked
- No new “capability claims” without artifacts (“No artifact, no capability” remains enforced).
- No autonomous execution introduced (advisory-only posture preserved).
- No changes to governance workflows, checks, or enforcement logic.
- Page remains consistent with AEO Stage 1: bounded decision space + explicit BLOCK legitimacy.

## 4) Evidence (repo pointers)
- Primary edited artifact:
  - `industrymodel.html`
- Existing governed artifacts referenced (no changes implied by this PR):
  - `governance/contracts/pp-door-release-v1.md`
  - `ops/reports/decision_trace.jsonl`
  - `ops/decisions/gate_result.json`
  - `ops/reports/system_status.json`
- Energy advisory artifacts referenced (expected/created in repo):
  - `governance/contracts/energy-output-stability-advisory-v1.md`
  - `governance/contracts/energy-peak-mitigation-advisory-v1.md`
  - `governance/rulesets/biw-door-energy-v1.json`
  - `ops/examples/energy_output_stability_advisory_*.json`
  - `ops/examples/energy_peak_mitigation_advisory_*.json`

## 5) Decision
**APPROVE** merging this PR once required checks pass.

Rationale:
- The change is documentation/spec structure only.
- It improves consistency between the main Stage 1 Proof Object and Stage 1.1 Energy Optimization use-case.
- It does not weaken governance posture or introduce ungoverned claims.

## 6) Expected outcome after merge
- `industrymodel.html` reads as one coherent normative spec.
- Stage 1.1 use-case is explicitly framed as **bounded advisory**, aligned with the Execution Control Layer and Decision Space.
- Governance checks remain mandatory and unchanged.
