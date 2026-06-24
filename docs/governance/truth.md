# Canonical System Truth

## Purpose

This repository operates under a single canonical system truth.

The purpose of this document is not to introduce new behavior,
but to explicitly declare which artifact represents the authoritative
state of the system.

## Canonical Truth Definition

The file

    ops/reports/system_status.json

is the **single canonical source of truth** for the system state.

All statements about:
- system state
- autonomy level
- governance mode
- health
- agent status

must be derivable from this file.

## Non-Canonical Artifacts

The following artifacts are **not truth**, but observations, inputs, or outputs:

- CI/CD logs
- runtime artifacts
- ops/events.jsonl
- decision traces
- monitoring outputs

They may:
- read from the canonical truth
- propose changes via Pull Request

They must **never silently redefine system truth**.

## Change Rule

Any change to canonical truth:

- MUST happen via Pull Request
- MUST be reviewable and diffable
- MUST be attributable (commit, actor, timestamp)

Direct mutation of system truth is considered invalid.

## Governance Note

This declaration is intentionally normative.

Technical enforcement will be incrementally strengthened,
but this document establishes the institutional rule
that all enforcement mechanisms must follow.
