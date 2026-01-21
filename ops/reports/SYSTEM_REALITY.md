## Canonical System Truth

The file `ops/reports/system_status.json` is the sole authoritative source
for system state, health, autonomy, and agent status.

All workflows, agents, dashboards, and governance gates MUST read from or
propose changes to this file.

No other file, event stream, or CI signal is considered system truth.
