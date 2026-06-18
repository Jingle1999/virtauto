# GEORGE Contract Catalog

## Runtime Governance Contracts

| Contract | Trigger | Decision |
|-----------|----------|----------|
| idle_loss_v1 | Production inactive + energy > threshold | BLOCK |
| shift_change_v1 | First minutes of shift | HOLD |
| variant_change_v1 | Variant transition | HOLD |
| production_recovery_v1 | Stable production recovered | ALLOW |
| quality_issue_v1 | Quality state NOK | HOLD |
| machine_failure_v1 | Machine state FAILURE | BLOCK |
| material_shortage_v1 | Buffer below threshold | HOLD |
| safety_violation_v1 | Safety state VIOLATION | BLOCK |

Default Governance State: HOLD