# decision_trace.md

## Decision / Intent
Introduce the **Status Agent** as the factory’s **Single Source of Truth** publisher.  
Goal: generate/maintain `ops/reports/system_status.json` deterministically via governed CI workflows (PR-based).

## Authority
- Class: **Governance / Operational Transparency**
- Authority level: **Supervised**
- Escalation: Guardian blocks on policy/security violations; human approval required for merge.

## Scope (files/modules touched)
- `scripts/status_agent.py` (Status Agent implementation / update)
- `agents/registry.yaml` (registry fields aligned to governance checks)
- `ops/consistency_agent.py` (consistency rules aligned to PASS/BLOCK model)
- `ops/validate_pr_decision_trace.py` (PR decision trace enforcement & accepted naming)

## Expected outcome
- All required governance checks pass (including Consistency Agent & PR decision trace requirement).
- Status Agent can be merged and will publish valid `ops/reports/system_status.json` as the canonical truth source.
- No dependency on `ops/decisions/gate_result.json` (PASS/BLOCK handled via CI result + artifacts).
