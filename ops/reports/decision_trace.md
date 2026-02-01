# Decision Trace

## Decision / Intent
Update governance-required workflow so PR checks are reliable and do not block merges due to missing merge-base fetch behavior.

## Authority
Maintainer: Jingle1999

## Scope (files/modules touched)
- .github/workflows/governance-required.yml

## Expected outcome
- PR checks run deterministically.
- No false negatives caused by git fetch depth / merge-base issues.
