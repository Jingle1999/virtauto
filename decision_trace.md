# Decision Trace for PR #512

## Decision / Intent
Fix Status Monitoring workflow so it can update truth artifacts on a protected main branch by creating/updating a PR instead of pushing directly.

## Authority
Repository maintainer.

## Scope
- .github/workflows/status-monitoring.yml

## Expected Outcome
- Workflow no longer fails due to protected branch push.
- Truth artifacts are proposed via PR (automation branch) and can be merged normally.

