# MAS Guardrails for virtauto (Agents controlling virtauto.de)

Derived from three sources (Agentic AI, Google AI Agents Guide, Umbrex Readiness Diagnostic).

## Self-Principles
- Self-organization, Self-regulation, Self-adaptation, Self-optimization, Self-determination.

## Grounding (Google)
- Declare **trusted data** per agent (e.g., Google Analytics, GitHub repo, sitemap, Medium RSS).
- Retrieval rules: source freshness, schema, and fallbacks when sources are unavailable.

## AgentOps / Observability (Google)
- Every agent emits **telemetry**: run id, inputs, outputs hash, errors, duration, decisions.
- Store in `/ops/run_telemetry.json` (append-only) and upload as CI artifact.

## Reproducibility (Google)
- Maintain **test cases** under `/tests/` with deterministic assertions (e.g., title/meta presence on homepage).
- CI runs tests and blocks merges on failure.

## Value-Anchoring (Umbrex)
- Each agent has a **Value Case** with KPI targets (e.g., broken links <= 0.5%, meta description coverage > 95%).

## Governance & Safe-to-Operate (Umbrex)
- RASCI defined for content, code, design, and releases.
- **Safe-to-operate baseline**: privacy/security, model/agent rollback, audit logs, human-in-the-loop for external changes.

## Continuous Readiness (Umbrex)
- Quarterly mini-diagnostic: refresh KPIs, heatmap, and 90-day plan.
