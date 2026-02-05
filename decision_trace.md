# Decision Trace — PR #509

## Decision / Intent
Fix status page truth/evidence fetch paths so the deployed page under `/status/` loads the correct JSON sources.

## Change Summary
- Update `TRUTH_PATH` to point to the deployed GitHub Pages path under `/status/...`
- Update `STATUS_AGENT_LOG_PATH` accordingly

## Authority
Repository owner / maintainers. Change is UI-only and does not execute autonomous actions.

## Scope (files/modules touched)
- status/index.html

## Expected Outcome
- `/status/` loads without “Truth Lock Failure”
- Truth source fetch succeeds (HTTP 200) at the correct deployed path
- Evidence source (JSONL) fetch succeeds (or is shown as missing without breaking the page)

## Validation Steps
1. Open https://www.virtauto.de/status/
2. DevTools → Network:
   - Confirm truth fetch returns 200:
     - `/status/ops/reports/system_status.json`
   - Confirm evidence fetch returns 200 (if present):
     - `/status/ops/agent_activity.jsonl`
3. DevTools → Console:
   - No fatal truth lock errors
   - Dashboard renders values from the truth source

## Risks
Low. Static path change only. Potential risk: wrong relative/absolute path causes truth lock failure.

## Rollback Plan
Revert this PR (or revert the commit) to restore previous paths.
