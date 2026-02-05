# Decision Trace — PR #511

## Decision / Intent
Fix status monitoring workflow so the Status Agent can update truth artifacts without direct pushes to protected main.

## Authority
Repository maintainer.

## Scope
- .github/workflows/status-monitoring.yml

## Change Summary
- Replace direct push-to-main with PR-based update flow for generated artifacts.

## Expected Outcome
- Scheduled runs open/update a PR when truth artifacts change.
- No direct pushes to protected branch.
- Status page receives fresh evidence via the PR merge path.

## Risks / Rollback
- If PR automation fails, revert workflow commit and run manually.
