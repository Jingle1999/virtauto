# Decision Trace – Mandatory Governance Artifact

## Rule

No decision may be merged without an explicit decision trace.

This is a hard governance rule.

## Purpose

Decision traces provide:
- accountability
- auditability
- post-hoc explainability

They do NOT justify correctness — only legitimacy.

## Accepted Formats

Exactly one of the following must exist per Pull Request:

- decision_trace.md
- decision_trace.json

## Minimum Required Fields

A decision trace MUST declare:

- decision_id
- decision_type (policy | structural | operational | content)
- authority_source (human | agent | contract | mixed)
- scope_of_impact
- intent
- expected_effect
- risks
- timestamp
- author

## Governance

Pull Requests without a valid decision trace:
- MUST be blocked
- MUST NOT be merged
- MUST be reviewed as invalid

This rule is enforced via governance-required checks.