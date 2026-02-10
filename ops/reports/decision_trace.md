# Decision Trace (Spec v1)

This repository is governed by an **audit-first Decision Trace**.
Every meaningful change (especially agent-triggered actions) must be explainable as a deterministic trace:

**route → execute → guardian → finalize**

The trace is not “documentation”. It is the **operational evidence** that a decision happened (or was blocked),
under explicit rules, and with a reproducible rationale.

---

## Canonical artifacts

### Runtime trace (authoritative)
- **Path:** `ops/reports/decision_trace.jsonl`
- **Format:** JSON Lines (one event per line)
- **Purpose:** Immutable-style append log of decisions across phases.

> If the UI or any implementation contradicts this log, the log wins.

### Optional legacy / snapshots
- `ops/reports/decision_trace.json` (snapshot/export, if used)
- `ops/reports/decision_trace.jsonl` is the canonical source.

---

## Trace contract (minimal)

Each trace entry SHOULD contain:

- `ts` (UTC ISO timestamp)
- `trace_id` (stable across phases)
- `phase` ∈ {`route`, `execute`, `guardian`, `finalize`}
- `actor` (e.g., `GEORGE`, `content_agent`, `GUARDIAN`)
- `decision_class`
- `intent`
- `status` (phase status)
- For `guardian`: `policy`, `checks[]`, `decision`, and `reason`

---

## Example: Website Agent BLOCK (Content publish)

This repository includes a real **BLOCK** example showing that agents can be stopped by design:

**Scenario**
- Content Agent requests publish (website update)
- Guardian evaluates policy
- Guardian blocks due to incomplete provenance (missing/placeholder commit reference)
- No publish is executed

**Where to find it**
- **Path:** `ops/reports/decision_trace.jsonl`
- **Trace ID:** `trace_content_publish_0001`
- **Decision class:** `CONTENT_PUBLISH`
- **Final:** `BLOCKED` (blocker: `GUARDIAN`)

**Swimlane**
1. `route` – GEORGE routes the publish intent
2. `execute` – content_agent prepares payload (no deploy yet)
3. `guardian` – policy checks; decision = BLOCK
4. `finalize` – GEORGE finalizes as BLOCKED; next_actions emitted

This is the proof that virtauto is **architecture-first**:
trust is created through bounded decision space + explicit stop mechanisms + audit evidence.

---

## Governance rule: PRs require decision trace

If a Pull Request changes behavior, user-facing output, policies, or core assets,
it must include a decision trace artifact update.

Minimum accepted: this file (`ops/reports/decision_trace.md`) and/or the runtime log
(`ops/reports/decision_trace.jsonl`) reflecting the intent and expected outcome.

---

## Notes

- Traces are append-only in spirit: do not rewrite history without an explicit governance decision.
- Use deterministic, minimal fields.
- If uncertain: log more evidence, not more narrative.
