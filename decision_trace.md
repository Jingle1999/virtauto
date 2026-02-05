# Decision Trace for PR #514

## Decision / Intent
Fix the Status Monitoring workflow so it can update “truth artifacts” even when `main` is protected:
- Generate/update a PR instead of pushing directly to `main`.
- Ensure staging/commit only includes files that actually exist to avoid git pathspec failures.

## Authority
Repository maintainer.

## Scope (files/modules touched)
- `.github/workflows/status-monitoring.yml`
- (optionally) `decision_trace.md` (this file)

## Context
The repository enforces branch protection on `main` (PR required, required checks, no bypass).
The scheduled Status Monitoring job must still publish refreshed evidence/truth artifacts regularly.

Previously, direct pushes to `main` from the workflow were blocked.
Additionally, attempts to `git add` paths that may not exist in a given run can fail with:
`fatal: pathspec '<file>' did not match any files`, preventing PR creation.

## Considered Options
1. **Allow GitHub Actions to bypass branch protection**
   - Rejected: weakens governance guarantees and undermines required checks/approvals.
2. **Push to a non-protected branch and open a PR**
   - Chosen: preserves branch protection, approvals, and required checks while enabling automation.

## Decision
Adopt PR-based updates for truth artifacts:
- Workflow writes/updates artifacts on a branch (automation branch).
- Workflow opens/updates a PR against `main` with only the relevant artifact paths.
- Only existing files are staged/committed to prevent pathspec errors.

## Expected Outcome
- Scheduled/manual Status Monitoring runs complete successfully.
- If artifacts change, a PR is created/updated automatically.
- Maintainers can review/merge under existing governance rules.
- No direct push to `main`; no staging failures due to missing files.

## Validation / How to Verify
1. Trigger the workflow manually (`Run workflow`) and/or wait for the schedule.
2. Confirm a PR is created/updated when artifacts change.
3. Verify required checks pass on the PR.
4. Merge PR and confirm `/status/` reflects refreshed timestamps/artifacts.

## Rollback Plan
Revert `.github/workflows/status-monitoring.yml` to the previous version.
(Note: rollback will likely restore the inability to update artifacts on protected `main`.)
