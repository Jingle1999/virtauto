# Phase 8 — Chaos Test (Deploy Capability)

Goal:
Prove deterministic failover for capability "deploy" without heuristics.

## Preconditions
- GitHub Pages uses "Deploy from GitHub Actions".
- Backup branch exists: `pages-backup`.
- Workflow exists: `.github/workflows/site-deploy.yml`.

## Test A (Deterministic failover via forced failure)
1) Go to Actions → "Deploy website (Pages) + Health & Auto-Rollback"
2) Click "Run workflow"
3) Set:
   - force_fail = true
   - override_url = (leave empty)
4) Run.

Expected:
- healthcheck job FAILS.
- rollback job RUNS.
- rollback deploys from