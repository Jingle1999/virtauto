## Conservative Autonomy Score v1 (Evidence-First)

### Intent
Compute a **conservative, deterministic autonomy percentage** that is never higher than what can be justified by local evidence.
Principle: **lower-but-certain beats higher-but-uncertain**.

### Inputs (local, deterministic)
- `ops/autonomy.json` (declared autonomy cap; treated as **upper bound only**)
- `ops/emergency_lock.json` (hard gate clamp)
- `ops/reports/decision_trace.jsonl` (trace presence & recency signal)
- `ops/reports/system_status.json` (generated output; freshness derived from `generated_at`)
- Agent snapshot (in `status_agent.py`, deterministic baseline)

### Method (conservative_autonomy_v1)
We compute:

1) **Gate clamp**
- `gate_factor = 1.0` if `gate_verdict == ALLOW`, else `0.0`

2) **Freshness penalty**
Based on minutes since `generated_at`:
- `<= 15 min` → factor `1.0` (FRESH)
- `15–60 min` → factor `0.5` (STALE)
- `> 60 min` → factor `0.2` (EXPIRED)
If unknown → `0.2`

3) **Trace signal (minimal)**
- If `decision_trace.jsonl` missing → `0.0` (MISSING)
- If present and last record is `<= 15 min` → `1.0` (LINKED_FRESH)
- Else → `0.5` (LINKED_STALE / UNVERIFIED)

4) **Agent coverage**
- `active_agents / total_agents`
- Active is counted only if `status == ok` and `state == ACTIVE`
- `total_agents` is fixed to `6` (dashboard expectation)

5) **Final score**
- `core = min(base_cap_percent, agent_coverage_percent)`
- `evidence_autonomy_percent = round(core * freshness_factor * trace_factor * gate_factor, 1)`

### Output fields
Written to `ops/reports/system_status.json` under:
- `autonomy_score.percent`
- `autonomy_score.details` (cap, coverage, freshness, trace labels)

Additionally, the full derivation is recorded in:
- `ops/reports/decision_trace.json` and appended to `ops/reports/decision_trace.jsonl`
under evidence: `ev_autonomy_score.details`.

### Safety posture
- Never exceeds declared autonomy (`ops/autonomy.json`) because it is used only as a **cap**.
- Never exceeds what is supported by **coverage**.
- Strongly degrades under **staleness** or missing trace.
- Hard-clamps to **0%** on emergency lock (DENY).
