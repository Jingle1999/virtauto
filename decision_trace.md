# Decision Trace for PR #515

## Decision / Intent

Stabilize and normalize the Status Monitoring pipeline so that the system status is
updated automatically, reliably, and governance-compliant over time.

The goal is to ensure that the public status page always reflects the latest
validated system state without manual intervention, while preserving branch
protection and review guarantees.

## Authority

Repository maintainer.

## Scope (files/modules touched)

- .github/workflows/status-monitoring.yml
- decision_trace.md (this file)

## Context

The repository enforces strict branch protection on `main`
(PR required, required checks, no bypass).

The Status Monitoring workflow is responsible for generating and publishing
authoritative “truth artifacts” (system status, decision trace, audit signals)
that are rendered on the public status page via GitHub Pages.

Previously observed issues:
- Direct pushes to `main` were blocked by branch protection.
- Partial or missing artifacts caused inconsistent or stale status displays.
- Workflow runs completed, but the published status did not advance reliably.

This created operational noise and undermined trust in the status signal.

## Considered Options

1. **Allow GitHub Actions to bypass branch protection**  
   Rejected: weakens governance guarantees and contradicts the system’s
   safety-first design principles.

2. **Publish status from a non-protected branch only**  
   Rejected: decouples the visible status from the governed source of truth
   (`main`) and risks drift.

3. **PR-based publication of truth artifacts (automation as a contributor)**  
   Chosen: preserves governance, maintains auditability, and enables
   fully automated yet reviewable updates.

## Decision

Adopt a PR-based model for status and truth artifact updates:

- The Status Monitoring workflow generates artifacts on an automation branch.
- The workflow opens or updates a pull request against `main`.
- Only existing and validated artifacts are staged and committed.
- All required checks and reviews apply before merge.
- GitHub Pages continues to publish exclusively from `main`.

This treats the automation as a governed system actor rather than a privileged bypass.

## Expected Outcome

- Status Monitoring runs complete deterministically.
- The public status page updates automatically after validated merges.
- No stale, partial, or misleading status signals.
- Zero manual intervention required in steady state.
- Governance guarantees remain intact.

## Validation / How to Verify

1. Observe a scheduled or manual Status Monitoring workflow run.
2. Confirm that a PR is created or updated when artifacts change.
3. Verify that required checks pass on the PR.
4. Merge the PR.
5. Confirm that the status page reflects the updated timestamps and artifacts.

---

**Decision status:** Approved  
**Operational impact:** Long-term stabilization  
**Governance alignment:** Fully compliant
