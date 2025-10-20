# AgentOps Playbook

- Each agent writes a JSON line per run to `/ops/run_telemetry.jsonl`.
- Include: timestamp, agent name, run_id, input summary, output hash, duration, error list, key decisions.
- CI uploads telemetry as artifact for audit.
- Weekly review: scan errors, regressions, and slow runs; file issues with owners.
