# Decision Trace — Status Agent (Phase 9)  
**Artifact:** `docs/decision_trace.md`  
**Scope:** `ops/status_agent.py` — deterministic truth regeneration for the Status Page (GitHub-native, no network)

---

## 1) Decision Summary (What is being approved?)

We approve the **Status Agent (Phase 1)** as a governed, deterministic workflow that **regenerates the Single Source of Truth** for the website status page and produces a **machine-readable decision trace**.

### The Status Agent generates / refreshes (authoritative artifacts)
- `ops/reports/system_status.json` *(primary truth rendered by /status/)*
- `ops/reports/decision_trace.json` *(explainability v1 — machine-readable)*
- `ops/reports/decision_trace.jsonl` *(append-only decision log)*
- `ops/decisions/gate_result.json` *(authoritative gate verdict snapshot)*
- `ops/agent_activity.jsonl` *(append-only activity evidence)*

### What changed in this approval (Option A + B)
- **Option A:** compute **trace coverage** (conservative) from the last N `decision_trace.jsonl` entries  
- **Option B:** compute **decision confidence** (very conservative) from hard evidence signals  
- Display **Confirmed Autonomy** only:  
  `confirmed_autonomy_percent = raw_autonomy_percent * decision_confidence`

> Governance principle: **low but true** beats **high but uncertain**.

---

## 2) Governance Objectives

This decision enforces:
1. **Single Source of Truth (SSOT)** for operational status (`system_status.json`)
2. **Deterministic traceability**: no decision without trace
3. **Conservative reporting**: autonomy is shown only when confidence is justified
4. **No hidden behavior**: append-only evidence logs (`*.jsonl`)
5. **Safety gate**: emergency lock hard-stops any “ALLOW” semantics

---

## 3) Inputs, Outputs, Evidence

### Inputs (read-only)
- `ops/autonomy.json` *(raw autonomy input, expected schema: overview.system_autonomy_level ∈ [0..1])*
- `ops/decisions/latest.json` *(last decision snapshot, optional for linking; required for confidence input check)*
- `ops/emergency_lock.json` *(hard safety lock; if locked=true → gate DENY and confidence=0)*
- `ops/reports/decision_trace.jsonl` *(for trace coverage computation; append-only log)*

### Outputs (written deterministically)
- `ops/reports/system_status.json`
- `ops/reports/decision_trace.json`
- `ops/reports/decision_trace.jsonl`
- `ops/decisions/gate_result.json`
- `ops/agent_activity.jsonl`

### Evidence (append-only)
- `ops/reports/decision_trace.jsonl` entries created per run
- `ops/agent_activity.jsonl` entry per run (includes confidence + coverage + verdict)

---

## 4) Deterministic Decision Logic

### 4.1 Gate Verdict (authoritative snapshot)
- If `ops/emergency_lock.json.locked == true` → `gate_verdict = DENY`
- Else → `gate_verdict = ALLOW`

### 4.2 Trace Coverage (Option A — conservative)
- Reads last `--trace-window` entries (default 50) from `ops/reports/decision_trace.jsonl`
- An entry counts as “valid” only if it contains minimum keys:  
  `schema_version, generated_at, trace_id, because, inputs, outputs, evidence`
- Coverage = `valid / total` (clamped; 0 if no traces)

### 4.3 Decision Confidence (Option B — very conservative)
Hard stop:
- If emergency lock is active → **confidence = 0.0**

Otherwise confidence starts at 0.0 and increases only with hard evidence:
- Inputs parseable and present (`autonomy.json`, `џьlatest.json`, `emergency_lock.json`) → **+0.20**
- Required outputs exist (after run) → **+0.30**
- Trace coverage ≥ 0.90 → **+0.30**
- Gate verdict == ALLOW → **+0.20**

Clamp to [0.0, 1.0].

### 4.4 Confirmed Autonomy (what the website should trust)
- `raw_autonomy_percent = clamp(autonomy.overview.system_autonomy_level, 0..1) * 100`
- `confirmed_autonomy_percent = raw_autonomy_percent * decision_confidence`
- Status page should treat **confirmed_autonomy_percent** as the KPI.

---

## 5) “Never” Clauses (Non-negotiable constraints)

The Status Agent **MUST NOT**:
- perform network calls, API requests, or external writes (repo-local only)
- deploy to production or publish content outside GitHub PR/workflow governance
- modify policies, authority matrices, or governance rules
- “invent” status values without traceable evidence
- bypass emergency lock

---

## 6) Acceptance Criteria (Definition of Done)

Phase 1 (Status Agent) is considered **DONE** when all conditions are met:

1. **Artifacts exist** after scheduled/manual run:
   - `ops/reports/system_status.json`
   - `ops/reports/decision_trace.json`
   - `ops/reports/decision_trace.jsonl`
   - `ops/decisions/gate_result.json`
   - `ops/agent_activity.jsonl`

2. **Determinism**
   - Running the agent on identical repo state yields identical structural outputs
   - No time-based randomness except `generated_at` / `trace_id` timestamps

3. **Safety**
   - Setting `ops/emergency_lock.json.locked=true` yields:
     - `gate_verdict = DENY`
     - `decision_confidence = 0.0`
     - Health signal becomes RED

4. **Conservative autonomy**
   - `autonomy_score.percent` represents **confirmed** autonomy
   - `autonomy_score.raw_percent` exists for transparency
   - Confidence and trace coverage are included in `autonomy_score`

5. **Trace completeness**
   - Each run appends a `decision_trace.jsonl` entry and an `agent_activity.jsonl` entry

---

## 7) Manual Verification Checklist (for reviewers)

- [ ] Open `/status/` and confirm it references the SSOT file path
- [ ] Confirm freshness updates after workflow run
- [ ] Confirm `gate_result.json` reflects emergency lock correctly
- [ ] Confirm `decision_trace.json` and `.jsonl` are updated each run
- [ ] Confirm `autonomy_score.decision_confidence` is ≤ 1.0 and conservative
- [ ] Confirm `autonomy_score.percent` == `raw_percent * decision_confidence`

---

## 8) Decision

**APPROVED:** Status Agent — Phase 1 (Truth Regeneration)  
**Mode:** Governed, deterministic, conservative reporting  
**Primary KPI:** Confirmed Autonomy (confidence-adjusted)

**Next:** Proceed with Option C and D end-to-end (authority enforcement and autonomy score strengthening) and re-evaluate confirmed autonomy after full chain verification.

---
