# virtauto.OS

Governed Industrial Multi-Agent Systems for Energy Optimization, Decision Intelligence and Industrial Operations.

virtauto.OS combines:

- Industrial Multi-Agent Systems (MAS)
- Human-in-the-loop governance
- Runtime observability
- Decision Intelligence
- Energy optimization workflows
- Governed industrial AI

Core governance pattern:

ALLOW → HOLD → BLOCK

Execution principle:

Advisory-first. Human approval required.

## Current Focus Areas

- BIW Energy Intelligence
- Governed Decision Layers
- Industrial Runtime Monitoring
- Energy Optimization Agents
- GEORGE Orchestration Layer
- Safe Industrial AI

## Product Components

- Runtime Surface
- Energy Scan
- Governance Contracts
- Decision Traceability
- Agent Orchestration

## What it does (safe defaults)
- Adds `<link rel="stylesheet" href="assets/styles_unify.css">` to each `*.html` (if missing).
- Normalizes all `<img>`:
  - wraps in `<figure class="media">...</figure>` (if not already wrapped)
  - adds `class="img-responsive"`
  - sets `loading="lazy"` and `decoding="async"`
  - removes inline width/height styles; preserves real pixel size as attributes when present
  - ensures every image has an `alt` text (fallback: file name)
- Tightens whitespace around cards/sections and unifies heading spacing.
- Writes a detailed log under `logs/ux-unify-*.log` with a dry-run option.

> The tool is **idempotent**: you can run it multiple times safely.

## Files
- `agents/ux_unify_agent.py` – orchestrator (CLI) that calls the tool and writes logs.
- `tools/site_unifier.py` – HTML rewriter using BeautifulSoup-like parsing (pure python stdlib + regex fallback).
- `assets/styles_unify.css` – small CSS additions that harmonize visuals without breaking your theme.
- `README.md` – this file.

## Quick start (local)
```bash
# from repo root (where your index.html lives)
python agents/ux_unify_agent.py --apply

# or dry run only
python agents/ux_unify_agent.py --dry-run
```

## Run in GitHub Actions (optional)
Add this step to your **self-agents** workflow before deployment:

```yaml
- name: Unify site visuals (images, figures, spacing)
  run: |
    python agents/ux_unify_agent.py --apply
```

> If you want the Action to commit back changes, add a step with `git config` + `git commit` + `git push` using a PAT or `GITHUB_TOKEN` with write permissions.
