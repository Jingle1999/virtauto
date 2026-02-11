# Authority Enforcement

Status: DONE

- All changes require Pull Requests
- Governance checks are mandatory
- Branch protection applies to all actors
- Administrative override is explicit, not silent

Authority is governing.

This repository operates under explicit governance.

## Core Rule

All changes to system state, behavior, or governance
MUST occur via Pull Request.

A Pull Request is a governance act.

## Administrator Authority

Repository administrators retain technical override capabilities
as a last-resort safety mechanism.

However:

- Any administrative override MUST be intentional.
- Any override MUST be documented via Pull Request or post-hoc decision trace.
- Silent or undocumented changes are considered governance violations.

## Enforcement Status

Branch protection rules are configured to:
- require Pull Requests
- require mandatory governance checks
- prevent accidental or implicit bypass

This establishes authority as governing, not advisory.
