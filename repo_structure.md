# virtauto Repository Structure

## Purpose

virtauto is an Industrial OS prototype focused on Decision Intelligence, Multi-Agent Systems (MAS), industrial orchestration, and operational governance for complex industrial environments.

The repository is intended to evolve into a modular, production-oriented architecture that separates:

- frontend applications,
- backend/runtime systems,
- orchestration logic,
- governance,
- operational tooling,
- and industrial data models.

The primary objective is to establish a clean and scalable foundation for the development of virtauto.OS.

---

# Core Repository Principles

1. The repository represents a system platform — not a collection of unrelated experiments.
2. Every module must have a clear operational responsibility.
3. Governance and traceability are first-class system components.
4. The repository must remain scalable for:
   - Energy Optimization
   - Industrial Decision Intelligence
   - Supply Chain MAS
   - Cross-domain orchestration
   - Industrial AI pilots
5. Experimental artifacts should be archived, not deleted.
6. The repository structure must support future production deployment.

---

# Target Repository Structure

```text
/apps
    /website
        Public frontend, landing pages, BIW Energy Scan,
        multilingual pages, public demos

    /api
        FastAPI backend, APIs, authentication,
        webhooks, ingestion endpoints

    /dashboard
        Internal operator dashboards,
        Trust & Governance dashboards,
        industrial monitoring interfaces


/core
    /agents
        Productive agents grouped by domain
        (energy, monitoring, governance, SCM, etc.)

    /orchestrator
        GEORGE orchestration engine,
        routing, coordination, conflict resolution

    /governance
        Decision Contracts,
        policies,
        HOLD-default logic,
        audit standards

    /memory
        embeddings,
        semantic memory,
        contextual knowledge structures

    /runtime
        BaseAgent,
        message bus integration,
        state management,
        execution runtime


/data
    /schemas
        Event schemas,
        decision schemas,
        telemetry structures

    /samples
        Sample datasets,
        demo CSV files,
        synthetic industrial datasets

    /generators
        Synthetic BIW generators,
        industrial simulation generators


/ops
    Monitoring,
    deployment,
    CI/CD,
    infrastructure,
    logging,
    operational tooling


/docs
    /architecture
    /roadmap
    /pilots
    /governance
    /operations

    System documentation,
    ADRs,
    implementation concepts,
    pilot documentation


/tests
    Unit tests,
    integration tests,
    orchestration tests,
    governance tests


/archive
    Legacy HTML files,
    .bak files,
    deprecated demos,
    outdated ZIPs,
    notebooks,
    experimental prototypes
