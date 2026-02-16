# Decision Trace — status_agent (Truth Regeneration, Phase 1)

## Decision / Capability
- **Capability ID:** status_agent.truth_regeneration.v1
- **Owner:** status_agent
- **Purpose:** Regenerate deterministic truth artifacts for the website and governance evidence.

## Trigger
- GitHub Actions schedule (heartbeat) and manual `workflow_dispatch` via `status-monitoring.yml`.

## Inputs (authoritative)
- `ops/autonomy.json` (single explicit autonomy source; conservative)
- `ops/decisions/latest.json` (optional pointer; does not change truth logic)
- `ops/emergency_lock.json` (authoritative lock switch)
- `ops/authority_matrix.yaml|json` (evidence only: existence/mtime/size)
- `ops/george_rules.yaml` (evidence only: existence/mtime/size)

## Outputs (truth + evidence)
- `ops/reports/system_status.json` (Single Source of Truth for website)
- `ops/reports/decision_trace.json` (machine-readable trace)
- `ops/reports/decision_trace.jsonl` (append-only trace log)
- `ops/agent_activity.jsonl` (append-only activity evidence)

## Gate Semantics (Guardian-style)
- **PASS** if `ops/emergency_lock.json` is not locked (or missing).
- **BLOCK** if `ops/emergency_lock.json` contains `"locked": true`.
- The workflow must **fail** on **BLOCK** (exit code) to enforce the gate.

## Determinism & Safety Envelope
- No network calls.
- No non-deterministic sampling.
- File evidence is **metadata-only** (existence, mtime, size); no content parsing in Phase 1.
- Missing/malformed input files are treated as **unavailable**, never as positive evidence.

## Authority / Autonomy
- **Autonomy mode:** `SUPERVISED` (conservative default).
- **Autonomy percent:** derived solely from `ops/autonomy.json.overview.system_autonomy_level` (0..1 clamped).
- Missing evidence must **not** increase autonomy.

## Failure Modes (expected behavior)
- Missing `ops/autonomy.json` → autonomy percent = 0.0
- Missing/malformed optional inputs → still generate truth; mark evidence as partial
- Emergency lock active → gate verdict **BLOCK**; workflow must stop

## Audit Evidence
- `ops/reports/decision_trace.jsonl` line appended per run
- `ops/agent_activity.jsonl` line appended per run
- GitHub Actions artifact upload containing all outputs
