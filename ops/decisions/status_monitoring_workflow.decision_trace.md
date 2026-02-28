# Decision Trace — status-monitoring workflow (Phase 1)

## Decision / Capability
- **Capability ID:** workflow.status_monitoring.phase1.v1
- **Owner:** GitHub Actions (status-monitoring.yml)
- **Purpose:** Run `status_agent` on a fixed heartbeat and publish evidence as an Actions artifact.

## Trigger
- Cron schedule (every 10 minutes)
- Manual dispatch (`workflow_dispatch`)

## Execution Steps (deterministic)
1. Checkout repository
2. Setup Python 3.11
3. Install dependencies if `requirements.txt` exists
4. Run `python ops/status_agent.py --env production`
5. Read verdict from `ops/reports/system_status.json` → `autonomy_score.gate_verdict`
6. Upload artifacts to GitHub Actions (always)
7. Enforce gate: fail job if verdict != PASS

## Artifacts Published (Actions artifact)
- `ops/reports/system_status.json`
- `ops/reports/decision_trace.json`
- `ops/reports/decision_trace.jsonl`
- `ops/agent_activity.jsonl`

## Gate Semantics
- PASS/BLOCK is enforced in the workflow (exit code).
- BLOCK must stop downstream automation (guardian-style hard stop).

## Audit Evidence
- GitHub Actions run log
- Uploaded artifact: `status-evidence-<run_id>-<attempt>`
