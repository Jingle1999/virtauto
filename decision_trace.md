# decision_trace.md

## Decision / Intent
Bootstrap governance artifacts required to merge the Status Agent onboarding PR(s).
Ensure CI gates pass deterministically without introducing a separate gate_result.json file.

## Authority
- Class: Governance / Operational Transparency
- Authority level: Supervised
- Escalation: Guardian blocks on policy/security violations; human approval required for merge.

## Scope (files/modules touched)
- ops/validate_pr_decision_trace.py (accept **/*.decision_trace.md)
- agents/registry.yaml (add required fields: autonomy_mode, state)
- ops/reports/system_status.json (bootstrap valid, registry-aligned status)
- ops/reports/decision_trace.jsonl (bootstrap valid trace entry)
- ops/consistency_agent.py (PASS/BLOCK via CI + artifacts; no gate_result.json requirement)

## Expected outcome
- `validate_pr_decision_trace` passes for PRs that include `**/*.decision_trace.md`.
- `Consistency Agent v1` passes: registry + system_status + decision_trace.jsonl are consistent and valid.
- No dependency on `ops/decisions/gate_result.json`; PASS/BLOCK handled by CI result and GitHub artifacts.
