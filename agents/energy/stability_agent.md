# Stability Agent

## Purpose
Evaluates whether operational stability could be affected by energy reduction proposals.

The agent protects operational availability, production continuity, takt stability and line resilience before optimization measures are considered admissible.

## Inputs
- takt stability
- buffer level
- station availability
- downtime events
- maintenance signals
- quality gate states
- cycle time deviations
- blocked station indicators
- shift state
- production mode

## Availability Protection
The agent continuously evaluates whether:
- line availability could degrade
- bottleneck stations could become unstable
- maintenance windows are violated
- recovery capability is reduced
- operational resilience drops below threshold

Availability protection has priority over energy optimization.

## Trigger
Activated when:
- an energy reduction proposal is generated
- a peak-load event occurs
- line instability is detected
- operational thresholds are exceeded

## Output
- ALLOW
- HOLD
- BLOCK
- ALERT

## Decision Logic
The agent evaluates whether:
- takt stability remains acceptable
- buffers are sufficient
- critical stations remain protected
- quality gates are not endangered
- downtime probability increases
- operational availability remains protected
- recovery capability remains sufficient

If operational risk exceeds defined thresholds, the proposal is blocked or delayed.

## Decision Impact
Can:
- block energy optimization proposals
- request operator review
- escalate runtime alerts
- enforce HOLD state during instability

## Runtime Role
Industrial safety and stability boundary for governed decision execution.

The Stability Agent acts as a safeguard between optimization intent and operational admissibility.

## Example Runtime Output

```json
{
  "agent": "stability",
  "state": "ACTIVE",
  "decision": "HOLD",
  "reason": "buffer below minimum threshold",
  "affected_line": "BIW-TVL-01",
  "operator_review_required": true
}
