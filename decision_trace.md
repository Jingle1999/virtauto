# Decision Trace — PR: Status Agent PASS/BLOCK + Artifact Evidence

## Decision / Intent
Align the Status Agent to the platform governance pattern:
- Use **PASS/BLOCK semantics** via process exit code (like Guardian).
- Publish deterministic truth + evidence as **GitHub Actions artifacts**.
- Remove the need for a separate `gate_result.json` truth artifact.

## Authority
- **Governance-first**: truth regeneration must be deterministic, auditable, and conservative.
- **Low-but-true beats high-but-uncertain**.
- **No additional mutable truth artifact** for “gate_result”; gate is expressed by PASS/BLOCK (exit code) and trace evidence.

## Scope (files/modules touched)
- `ops/status_agent.py`
- `.github/workflows/status-monitoring.yml`
- `agents/registry.yaml`
- `ops/consistency_agent.py`
- `decision_trace.md`

## Expected Outcome
1. **CI checks pass**
   - `Consistency Agent v1` no longer expects `ops/decisions/gate_result.json`.
   - `agents/registry.yaml` contains required fields: `state`, `autonomy_mode`.
   - `ops/reports/decision_trace.json` conforms to required keys (`schema_version`, `generated_at`, `trace_id`, `inputs`, `outputs`, `because`).

2. **Operational behavior**
   - Status Agent runs on schedule.
   - Produces:
     - `ops/reports/system_status.json`
     - `ops/reports/decision_trace.json`
     - `ops/reports/decision_trace.jsonl`
     - `ops/agent_activity.jsonl`
   - Uploads these as a **GitHub Actions artifact** each run.
   - If `ops/emergency_lock.json` indicates `locked=true`, the job **BLOCKS** (exit code 2), and evidence still uploads (via `if: always()`).

## Risk / Trade-offs
- Removing `gate_result.json` requires updating any checks that previously depended on it.
- If other workflows expect `gate_result.json`, they must be migrated to PASS/BLOCK semantics or to reading `decision_trace.json` / `system_status.json` for gate state.

## Rollback
Revert these files to prior versions and re-introduce `ops/decisions/gate_result.json` + associated checks if required by downstream tooling.
