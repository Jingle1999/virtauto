# Decision Trace (PR): Relax PR Decision Trace Enforcement to PR-Scoped Files

## Decision / Intent
Fix governance deadlock by allowing PR-scoped decision traces.
Goal: Accept `decision_traces/**/*.decision_trace.md|json` in addition to root `decision_trace.md|json`.

## Authority
- Class: Governance / Traceability
- Level: Supervised
- Escalation: Human approval required for merge

## Scope (files/modules touched)
- ops/validate_pr_decision_trace.py

## Expected outcome
- validate_pr_decision_trace check passes when a PR adds/modifies a PR-scoped decision trace.
- Avoid merge conflicts and circular failures across parallel PRs.
