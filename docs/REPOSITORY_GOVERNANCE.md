# Repository Governance Specification v1.0

**Project:** virtauto.OS
**Version:** 1.0
**Status:** Draft (Governance Baseline)
**Date:** 2026-06-25

---

# 1. Purpose

This document defines the governance principles for the **virtauto.OS** repository.

Its purpose is to ensure that the repository evolves as a coherent industrial software platform instead of becoming a collection of independent experiments.

The repository serves as the technical foundation for **virtauto.OS**, an Industrial Decision Platform that combines operational data, governance contracts, industrial reasoning, and human decision-making into a unified runtime environment.

---

# 2. Repository Mission

The repository shall support the development of:

* Industrial Decision Intelligence
* Governed Multi-Agent Systems
* Decision Contracts
* Runtime Governance
* Human-in-the-Loop Operations
* Industrial AI Pilots
* Decision Traceability

Every contribution should strengthen one or more of these capabilities.

---

# 3. Repository Principles

The following principles govern all future development.

## Principle 1 — Platform First

The repository represents a software platform rather than a collection of unrelated projects.

Every component must contribute to the long-term architecture.

---

## Principle 2 — Governance by Default

Every operational decision shall be explainable, reproducible and auditable.

No autonomous behaviour may bypass governance contracts.

---

## Principle 3 — Runtime Before Automation

Automation is only permitted after the corresponding runtime behaviour can be observed, explained and tested.

The Runtime Surface is therefore considered a first-class system component.

---

## Principle 4 — Evolution Instead of Rewrite

Existing functionality should be migrated gradually.

Working software shall never be replaced by architecture diagrams alone.

---

## Principle 5 — Archive Instead of Delete

Experimental artefacts, obsolete prototypes and historical implementations should normally be archived rather than deleted.

The repository itself documents the evolution of virtauto.OS.

---

# 4. Productive Repository Areas

The following directories are considered production or production-ready components.

```
.github/
status/
ops/
tests/
docs/

virtauto_core/
virtauto_agents/
virtauto_governance/
virtauto_api/
virtauto_data/
```

These directories receive priority during maintenance and review.

---

# 5. Legacy Components

The repository currently contains legacy website files and historical prototypes.

These files remain part of the repository until they can be safely migrated.

Examples include:

* legacy HTML pages
* historical demos
* obsolete experiments
* backup files
* previous runtime prototypes

Legacy components shall not be removed without verifying production dependencies.

---

# 6. Website Protection Rule

The current public website is generated from the existing HTML structure.

Therefore:

**No HTML page shall be moved, renamed or deleted until its production dependency has been verified.**

Architecture improvements shall not interrupt the public website.

---

# 7. Target Architecture

The long-term target architecture is organised into logical domains.

```
apps/
    website/
    dashboard/
    api/

core/
    runtime/
    orchestrator/
    governance/
    agents/

data/
    schemas/
    samples/
    generators/

ops/
    deployment/
    monitoring/
    logging/

docs/
    architecture/
    governance/
    roadmap/

tests/
    unit/
    integration/
    governance/

Archive/
    legacy/
    deprecated/
    experiments/
```

This structure represents the architectural direction of virtauto.OS.

Migration shall be incremental.

---

# 8. GEORGE Runtime Architecture

GEORGE acts as the industrial decision orchestrator.

Every operational decision follows the same execution model.

```
Decision Contracts
        ↓
Decision Kernel
        ↓
GEORGE Router
        ↓
Runtime State
        ↓
Audit Trace
        ↓
Human Review
```

This execution chain forms the foundation of the Industrial Decision Platform.

---

# 9. Decision Governance

Every runtime decision shall contain at least:

* decision_id
* timestamp
* contract_id
* runtime_state
* decision
* reasoning
* evidence
* governance status
* audit trace

Missing information shall prevent autonomous execution.

---

# 10. Decision Priority

The default execution priority is

```
BLOCK
↓
HOLD
↓
ALLOW
```

If multiple contracts produce decisions of equal severity, domain priorities apply.

Current domain priority:

```
Safety
↓
Quality
↓
Machine
↓
Material
↓
Production
↓
Energy
```

These priorities may evolve as additional industrial domains are introduced.

---

# 11. Repository Evolution Policy

Repository changes shall follow this sequence:

1. Define governance.
2. Stabilise runtime behaviour.
3. Verify automated tests.
4. Introduce new functionality.
5. Refactor architecture.
6. Archive obsolete components.

Architecture changes shall never compromise runtime stability.

---

# 12. Next Milestones

The immediate priorities are:

1. Repository Inventory v1
2. CONTRACT_CATALOG.md completion
3. Runtime Decision Validation
4. Audit Trace standardisation
5. Runtime Surface connected to live outputs
6. Minimal virtauto_api implementation
7. Docker infrastructure
8. First production-grade Industrial Agent

---

# 13. Long-Term Vision

virtauto.OS evolves towards an **Industrial Decision Platform** where governed decision-making becomes the central operating layer between industrial data, AI agents and human operators.

The objective is not autonomous software.

The objective is **governed operational decision-making**.
