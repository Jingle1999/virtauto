# Decision Trace (PR): Align Consistency Agent with PASS/BLOCK + GitHub Artifacts

## Decision / Intent
Remove repo-dependency on gate_result.json and enforce only schema-level traceability.
Goal: Consistency Agent validates registry fields and decision_trace.jsonl schema, not artifact-in-repo files.

## Authority
- Class: Governance / Operational Consistency
- Level: Supervised
- Escalation: Human approval required for merge

## Scope (files/modules touched)
- ops/consistency_agent.py
- ops/reports/decision_trace.jsonl

## Expected outcome
- Consistency Agent passes without requiring ops/decisions/gate_result.json.
- Latest decision trace entry is schema-valid and references ops/reports/system_status.json.
