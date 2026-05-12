# virtauto – Phase 2: Self‑Agents Activation
Date: 2025-10-14

This bundle makes your current CI behave like *proto self‑agents*. It adds:
- **Self Agents Registry** (`self-agents.yml`)
- **GEORGE Orchestrator** (workflow to run & aggregate checks)
- **Agent jobs**: Lighthouse (perf/SEO/a11y/bp), Link Doctor, Security Headers
- **Config** for URLs & thresholds
- **Issue template** for clean reports

> Safe-by-default: file names do not overwrite your current workflows (`site_guardian.yml` stays).

## Install (2 minutes)
1. Unzip into your repo root (it creates `.github/workflows/`, `config/`, and `templates/`).  
2. Commit:
   ```
   chore(agents): add Phase 2 self-agents registry + orchestrator
   ```
3. Run manually once in GitHub → **Actions** → **GEORGE Orchestrator** → *Run workflow*.
4. After first run, check "Artifacts" & created issue **[GEORGE] Site Health Report**.

## Files
- `self-agents.yml` – registry of agents with goals, owners, schedules & thresholds
- `.github/workflows/george_orchestrator.yml` – runs agents (matrix), aggregates outputs, opens a single report issue
- `.github/workflows/self_agents.yml` – convenience workflow to run specific agent(s) on demand
- `config/urls.txt` – list of public URLs to audit
- `config/thresholds.yml` – score gates for GEORGE (Lighthouse perf/a11y/SEO/bp)
- `templates/issue_report.md` – templated issue body

## Customize
- Add or remove URLs in `config/urls.txt`.
- Adjust gates in `config/thresholds.yml`.
- Change owners in `self-agents.yml`.
- To pause daily schedule, comment out the `schedule:` blocks inside workflows.

## Rollback
Delete the added files and commit. No state is persisted.
