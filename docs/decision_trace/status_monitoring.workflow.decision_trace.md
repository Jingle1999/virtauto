# Decision Trace — Workflow: status-monitoring.yml (PASS/BLOCK + Truth Regeneration)

## Scope
This document defines the governance/decision flow enforced by:
- `.github/workflows/status-monitoring.yml`

The workflow turns status regeneration into a **governed, gated operation** with explicit **PASS/BLOCK** semantics aligned to the Guardian.

---

## Actors (Workflow-Level)
- `guardian_agent` (governance enforcement)
- `status_agent` (truth regeneration)
- `github_actions` (execution substrate)

---

## Step-by-step Decision Flow

### 1) Guardian Gate (job: `guardian_gate`)
**Purpose:** enforce governance before any truth mutation.

**Execution:**
- Run Guardian primary; if primary fails, run Guardian backup.
- Read `ops/reports/governance_outputs.json`:
  - `verdict`: PASS|BLOCK
  - `reasons`: list (optional)

**Enforcement:**
- If `verdict != PASS` → job fails (exit code 2)
- Downstream jobs are blocked.

**Evidence outputs (minimum):**
- `ops/reports/governance_outputs.json`
- `ops/reports/guardian_trace.jsonl`
- `ops/agent_activity.jsonl`

**Audit requirement:**
- Upload as GitHub artifact:
  - `status-guardian-gate-evidence-${run_id}-${run_attempt}`

---

### 2) Status Agent Truth Regeneration (job: `status_agent`)
**Purpose:** generate SSOT artifacts only under governance PASS.

**Precondition:**
- `needs: guardian_gate` (and guardian_gate must pass)

**Inputs:**
- `STATUS_GATE_VERDICT` from job output
- `STATUS_GATE_REASONS` from job output

**Outputs:**
- `ops/reports/system_status.json`
- `ops/reports/decision_trace.json`
- `ops/reports/decision_trace.jsonl`
- `ops/agent_activity.jsonl`

**Audit requirement:**
- Upload as GitHub artifact:
  - `status-evidence-${run_id}-${run_attempt}`

---

### 3) Publishing (job: `publish_status_pages`) — Optional
**Purpose:** publish `/status/` snapshot to Pages-served branch.

**Mechanism:**
- Checkout `status-pages`
- Bring `status/` folder from `main` snapshot
- Commit only if changed
- Force-push `status-pages`

**Note:**
Publishing is not part of governance. It is a **read-only transport** of already-gated outputs.

---

## System Guarantees
- **No truth mutation without PASS** (enforced by job dependency and hard failure).
- **No separate `gate_result.json`** (gate is represented via Guardian outputs and status trace fields).
- **Audit evidence is always preserved** (GitHub artifacts).
- **Website publishing is optional** and decoupled from audit.

---

## Failure Modes
1. Guardian BLOCK
   - Workflow stops before truth mutation.
   - Gate evidence artifact still uploaded.
2. Status Agent blocks itself (safety net)
   - If it receives gate != PASS (unexpected), exits non-zero.
   - Evidence artifacts still uploaded.
3. Publish failure
   - Does not affect governance decisions; truth artifacts remain in artifacts.
