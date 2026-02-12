## Phase 1/9 — Authority & Policy Evidence (Audit-Ready)

### Intent
Make governance enforcement **auditable** in the Single Source of Truth (SSOT) by attaching deterministic evidence that:
- an authority matrix exists (decision rights / escalation),
- policy rules exist (governed routing / constraints),
without relying on “trust me” statements.

### Inputs (local, deterministic)
- `ops/authority_matrix.yaml` or `ops/authority_matrix.json` (either one is acceptable)
- `ops/george_rules.yaml`

### Evidence method (dependency-free)
The Status Agent records file evidence only:
- `present` (boolean)
- `bytes` (file size)
- `mtime_utc` (UTC timestamp)

No YAML/JSON parsing is performed at this stage to keep execution safe and deterministic in GitHub Actions.

### Outputs
- SSOT: `ops/reports/system_status.json` → `governance_evidence.{authority,policies}`
- Trace: `ops/reports/decision_trace.json(.l)` includes:
  - `AUTHORITY_EVIDENCE_PRESENT/MISSING`
  - `POLICY_EVIDENCE_PRESENT/MISSING`
  - evidence refs with file evidence details

### Conservative posture
Missing authority/policy evidence must **not** increase autonomy. The autonomy score remains evidence-first and conservative.
