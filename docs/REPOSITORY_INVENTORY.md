# REPOSITORY_INVENTORY.md

Status: Draft inventory based on uploaded repository ZIP `virtauto-main (64)(1).zip`  
Strategy: Variant A — Evolution, not revolution.  
Date: 2026-06-25

## 1. Executive Summary

The repository currently contains **714 files** across **161 directories**. The architecture already contains the right evolutionary core: `status/`, `virtauto_core/`, `virtauto_governance/`, `tests/`, `assets/`, `images/`, and the public website files. The main issue is not the absence of structure, but overlapping historical structures and legacy material that should be classified before moving anything.

Recommended direction: keep the current working website stable, keep the GEORGE runtime kernel in place, document ownership, and clean up step by step. Do **not** move root-level HTML files until all website dependencies and GitHub Pages behaviour are checked.

## 2. Repository Statistics

| Area | Count / Observation |
|---|---:|
| Total files | 714 |
| Total top-level directories | 32 |
| Root-level files | 58 |
| `.md` files | 162 |
| `.py` files | 112 |
| `.json` files | 98 |
| `.html` files | 80 |
| `.txt` files | 41 |
| `.yml` files | 37 |
| `.bak` files | 31 |
| `.yaml` files | 29 |
| `.docx` files | 18 |
| `.pyc` files | 16 |
| `.js` files | 13 |
| `[none]` files | 11 |

## 3. Top-Level Directory Inventory

| Directory | Files | Initial Classification | Comment |
|---|---:|---|---|
| `.github/` | 33 | review | Many archived workflows. Review before changing branch/CI behaviour. |
| `agents/` | 12 | review | Agent documentation and older agent scripts. Needs alignment with future virtauto_agents. |
| `Archive/` | 211 | archive | Already intended for old material. Keep as archive target. |
| `assets/` | 16 | productive |  |
| `audit/` | 2 | review |  |
| `capabilities/` | 2 | review |  |
| `cdt/` | 2 | review |  |
| `config/` | 4 | review |  |
| `content/` | 10 | review |  |
| `decision_traces/` | 101 | review |  |
| `demo/` | 3 | review |  |
| `docs/` | 4 | productive |  |
| `governance/` | 29 | review | Older/parallel governance structure. Compare with virtauto_governance before merging. |
| `images/` | 7 | productive |  |
| `img/` | 2 | archive candidate | Likely duplicate of images/. Do not delete before reference check. |
| `logs/` | 4 | review |  |
| `memory/` | 21 | review |  |
| `monitoring/` | 3 | review |  |
| `ops/` | 107 | review | Large historical operations area. Contains useful GEORGE material but needs sorting. |
| `partials/` | 1 | review |  |
| `policies/` | 5 | review |  |
| `rules/` | 8 | review |  |
| `schemas/` | 1 | productive |  |
| `scripts/` | 15 | review |  |
| `self_healing/` | 8 | review |  |
| `src/` | 3 | productive |  |
| `status/` | 9 | productive | Public runtime surface and JSON status artifacts. Treat as live website-critical. |
| `tests/` | 4 | productive | Current test location. Needs expansion for router priority and trace format. |
| `tools/` | 15 | review |  |
| `virtauto.egg-info/` | 5 | archive candidate |  |
| `virtauto_core/` | 1 | productive | Current GEORGE decision kernel. Keep small and protected. |
| `virtauto_governance/` | 8 | productive | Current runtime contracts and schemas. Strong Phase 0 asset. |

## 4. Productive Core — Keep and Stabilize

These areas form the current working virtauto.OS baseline:

- `status`
- `virtauto_core`
- `virtauto_governance`
- `tests`
- `assets`
- `images`
- `src`
- `schemas`
- `README.md`
- `CNAME`
- `index.html`
- `index-de.html`
- `virtauto-os.html`
- `virtauto-os-de.html`
- `biw-energy.html`
- `biw-energy-de.html`
- `pilot.html`
- `pilot-de.html`
- `contact.html`
- `contact-de.html`
- `impressum.html`
- `imprint.html`
- `privacy.html`
- `sitemap.xml`
- `robots.txt`
- `package.json`
- `package-lock.json`
- `requirements.txt`
- `setup.py`

Primary interpretation: `status/` is the live runtime surface; `virtauto_core/decision_kernel.py` is the current GEORGE decision kernel; `virtauto_governance/contracts/` contains the current runtime contracts; `tests/` is the starting point for automated validation.

## 5. Runtime and Governance Inventory

### 5.1 `status/`

- `status/agent_reports.md`
- `status/agents.html`
- `status/dashboard_summary.json`
- `status/governed_decision.json`
- `status/index-de.html`
- `status/index.html`
- `status/latest_decision.json`
- `status/status.json`
- `status/system_health.json`

### 5.2 `virtauto_core/`

- `virtauto_core/decision_kernel.py`

### 5.3 `virtauto_governance/`

- `virtauto_governance/contracts/idle_loss.yaml`
- `virtauto_governance/contracts/machine_failure.yaml`
- `virtauto_governance/contracts/production_recovery.yaml`
- `virtauto_governance/contracts/quality_issue.yaml`
- `virtauto_governance/contracts/shift_change.yaml`
- `virtauto_governance/schemas/decision_evidence.json`
- `virtauto_governance/schemas/decision_trace.json`
- `virtauto_governance/schemas/runtime_state.json`

### 5.4 `tests/`

- `tests/README.md`
- `tests/system_test.py`
- `tests/test_george_orchestrator_v2.py`
- `tests/test_orchestrator_basic.py`

## 6. Review Zones — Useful but Not Yet Canonical

These areas likely contain valuable material, but they overlap with the new runtime/governance structure and should be reviewed before moving or deleting anything:

- `ops`
- `agents`
- `governance`
- `scripts`
- `tools`
- `monitoring`
- `memory`
- `policies`
- `rules`
- `config`
- `capabilities`
- `cdt`
- `demo`
- `content`
- `partials`
- `self_healing`
- `decision_traces`
- `logs`
- `audit`
- `PATCH_NOTES_GEORGE_CONTRACT.md`
- `repo_structure.md`
- `decision_trace.md`

Priority review order: `ops/` → `governance/` → `agents/` → `decision_traces/` → `scripts/` → `tools/`.

## 7. Archive / Legacy Candidates

These items are not immediate delete candidates. They are candidates for archive, dependency checks, or later consolidation:

- `Archive`
- `img`
- `404.html`
- `agents.html`
- `architecture.html`
- `app.js`
- `blog.html`
- `decision-demo.html`
- `decision-demo-de.html`
- `decision-model.html`
- `decision-model-de.html`
- `decision-trace.html`
- `energy-optimization.html`
- `energy-steel.html`
- `energy-steel-de.html`
- `energydecisionlayer.html`
- `footer.html`
- `george.html`
- `header.html`
- `healthcheck_job.yml`
- `solutions.html`
- `styles.css`
- `script.js`
- `status.js`
- `site-nav.js`
- `test_decision_kernel.py`
- `tidy_html_heads.py`
- `usecases.html`

Important rule: root-level HTML files may be legacy-looking, but many may still be linked directly by GitHub Pages. Do not move them until link checks pass.

## 8. Known Structural Tensions

- Two governance areas exist: `governance/` and `virtauto_governance/`. The current runtime should prefer `virtauto_governance/`; older strategic/governance docs can remain in `governance/` until mapped.
- Two image areas exist: `images/` and `img/`. Check HTML references before consolidation.
- `ops/` contains useful GEORGE history, schemas, traces, and runtime experiments, but is too broad to be treated as one productive module.
- `Archive/` already contains many files and should become the only target for deprecated material.
- Root remains website-critical because GitHub Pages appears to serve many files directly from root.

## 9. Target Structure — Evolutionary Variant A

```text
virtauto/
├── status/                 # live runtime surface and status JSON
├── virtauto_core/          # GEORGE kernel, router, message bus
├── virtauto_governance/    # active decision contracts and schemas
├── tests/                  # runtime, governance, router tests
├── assets/                 # shared frontend assets
├── images/                 # canonical image assets
├── docs/                   # repository governance, architecture, catalogs
├── virtauto_api/           # later: minimal health + latest decision API
├── virtauto_agents/        # later: clean agent slots
├── Archive/                # legacy, broken, deprecated, experiments
└── root HTML files         # keep until GitHub Pages dependency map is complete
```

## 10. Immediate Next Actions

1. Add this file as `docs/REPOSITORY_INVENTORY.md`.
2. Add `docs/REPOSITORY_GOVERNANCE.md` as the rulebook for what may be moved.
3. Run a link/dependency check for all root-level HTML files.
4. Create `docs/CONTRACT_CATALOG.md` or finalize the existing catalog from `virtauto_governance/contracts/`.
5. Expand tests: all contracts → GEORGE router → final decision.
6. Add priority test: `BLOCK > HOLD > ALLOW`, then domain priority.
7. Decide one canonical trace destination and mark all others as legacy/reference.

## 11. Working Rule

The repository should evolve from a public website plus experiments into a governed industrial runtime. The first goal is not cosmetic cleanup. The first goal is to protect the current working decision runtime while making every file understandable, traceable, and classifiable.
