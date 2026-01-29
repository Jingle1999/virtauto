# Decision Trace

## Context
This change updates the status monitoring and truth regeneration mechanism of the virtauto website.

## Decision
We enable deterministic, scheduled truth regeneration via a supervised status agent.

## Why
- Website state must reflect governed, reviewable decisions
- Status must not depend on manual updates
- Truth must be reproducible from repository state

## Authority
Approved via GitHub Pull Request with mandatory review and governance checks.

## Scope
- Affects website status reporting
- No autonomous execution of actions
- Read-only, observational agent

## Risks
- False GREEN status if upstream artifacts are incorrect
- Mitigated via emergency_lock and gate checks

## Outcome
Status truth is regenerated automatically, traceably, and without side effects.