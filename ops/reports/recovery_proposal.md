# Recovery Proposal (Self-Healing v1)

Timestamp (UTC): TBD

## Detected Condition

- Regression ID: R0
- Type: HEALTH_OR_GATE_ANOMALY
- Severity: blocking

## Anomalies

- TBD (list anomalies or say "none")

## Evidence

- System status: ops/reports/system_status.json
- Gate result: ops/decisions/gate_result.json
- Self-healing trace: ops/reports/self_healing_trace.json

## Proposed Recovery

This proposal does **not** execute changes autonomously.
It creates a draft PR for human governance to review and decide.

## Recommended review checklist

1. Confirm the anomaly in `ops/reports/system_status.json` / `ops/decisions/gate_result.json`.
2. Inspect recent decision traces for root-cause signals.
3. If gate verdict is `DENY`, identify which rule/gate blocked and why.
4. Approve the minimal fix PR only if it is deterministic and governed.

## Files Included In This Proposal

- ops/reports/recovery_proposal.md
