# virtauto.OS — System Overview (Knowledge Base Root)

**Document ID:** doc-001  
**Role:** Core knowledge document for the world’s first Agentic Website (virtauto.de).  
**Scope:** High-level architecture, agents, layers, and self-governance model.

---

## 1. Purpose of virtauto.de

virtauto.de is not a traditional website.

It is a **living, agentic system** that:

- observes itself,
- protects itself,
- writes and curates its own content,
- maintains its own status dashboard,
- and evolves over time through human–AI co-development.

virtauto.OS is the internal name for this architecture:  
> *“The Operating System behind the world’s first Agentic Website.”*

This document is the **root of the RAG knowledge base** for virtauto.de.

---

## 2. High-Level Architecture

virtauto.OS is structured into several layers:

1. **Interface Layer (Website UI)**
   - Static pages (`index.html`, `status/agents.html`, etc.)
   - CSS theme (`assets/styles.css`)
   - Status and activity components (agent health badge, mini-dashboard, activity feed)

2. **Agent Orchestration Layer**
   - Orchestrator: **GEORGE**
   - Self and utility agents:
     - `self_guardian` — immune system (security & policy guardian)
     - `monitoring` — heartbeat, logs, status JSON
     - `content` — content generation and curation for virtauto.de
     - `self_content` — meta-content about the system itself
     - planned: `audit`, `deploy`, `knowledge` (RAG)

3. **Automation & Infrastructure Layer**
   - GitHub repository as the **execution substrate**
   - 17+ GitHub Actions workflows for:
     - security checks
     - content ingestion
     - design & review gates
     - deployment and rollback
   - Status files:
     - `/status/status.json` — live agent health + pipelines
     - `/ops/events.jsonl` — activity / event log
     - `/ops/agent_reports.md` — human-readable guardian reports

4. **Knowledge & Memory Layer (RAG)**
   - `memory/index.json` — registry of knowledge documents
   - `memory/documents/*.md` — canonical knowledge documents
   - `memory/embeddings/*` — (future) vector representations for retrieval
   - content-ingest workflows to sync external sources (e.g. Medium) into the knowledge base

5. **Policy & Governance Layer**
   - `policies/*.md` and `governance/*` — security, compliance and design rules
   - `self_guardian.yml` — configuration of automated guardian checks
   - branch protection + PR-based change flow (no direct pushes to `main`)

---

## 3. Agent Roster and Responsibilities

### 3.1 GEORGE — Orchestrator

- Central coordinating entity of virtauto.OS.
- Plans and triggers workflows and agents based on:
  - repository changes,
  - schedules,
  - status and events,
  - future: explicit rules in `ops/george_orchestrator.py` and `ops/george_rules.yaml`.
- Long-term goal: act as the **prefrontal cortex** of the system.

### 3.2 Self_Guardian

- Immune system of virtauto.de.
- Responsibilities:
  - run security and policy checks on each relevant PR,
  - enforce repository rules and design tokens,
  - create guardian reports and comments in PRs,
  - protect `main` via automated gates.
- Evidence:
  - 20+ guardian-related PRs,
  - dedicated security workflows in `.github/workflows`.

### 3.3 Monitoring Agent

- Observability and heartbeat.
- Maintains:
  - `/status/status.json` with live counts (OK / issues / unknown),
  - timestamps for latest checks and reports,
  - input for the **Self-Agent Dashboard**.
- Supports the mini-dashboard on `index.html` and the detailed view on `status/agents.html`.

### 3.4 Content Agent

- Generates and updates website content:
  - landing page elements,
  - solution descriptions,
  - knowledge base items.
- Works together with `self_content` and future `knowledge` agent.

### 3.5 Self_Content Agent

- Meta-narrative layer.
- Writes content **about** virtauto.de as a system:
  - e.g. “Hello World – I Am virtauto.de. The World’s First Agentic Website”
  - PRs that describe the system, its evolution and self-awareness.
- Connects to external channels (e.g. Medium) via content-ingest workflows.

### 3.6 Planned Agents

- **Audit Agent**  
  - Deeper compliance and log review, across policies and runtime behaviour.

- **Deploy Agent**  
  - Automated, policy-aware deployment and rollback of website versions.

- **Knowledge / RAG Agent**  
  - Ingestion of documents into `memory/documents`  
  - Management of embeddings and retrieval for future question-answering.

---

## 4. Data & Knowledge Flows

### 4.1 From External Sources to Memory

Typical path for new knowledge:

1. Article or document is created (e.g. Medium post about virtauto).
2. A content-ingest or manual workflow:
   - pulls the content,
   - writes a `.md` file into `memory/documents`,
   - updates `memory/index.json` with:
     - `id`, `title`, `type`, `tags`, `path`, `summary`.
3. Future RAG workflow:
   - generates embeddings into `memory/embeddings`,
   - registers document chunks for retrieval.

### 4.2 From Memory to UI and Agents

- Agents consult the knowledge layer to:
  - generate consistent descriptions of virtauto.OS,
  - maintain the architecture pages and knowledge base section,
  - support future question-answering and diagnostics.
- UI components (e.g. knowledge base section on `index.html`) point to:
  - curated articles,
  - agent-of-the-week posts,
  - Industrial Tech Chronicles.

---

## 5. Self-X Capabilities

virtauto.OS is designed around **Self-** principles:

1. **Self-Organization**
   - Agents are modular and loosely coupled.
   - New agents (audit, deploy, knowledge) can be added without redesigning the whole system.

2. **Self-Regulation**
   - Guardian workflows enforce compliance and security.
   - PR-based flow ensures that changes are reviewed by humans and agents.

3. **Self-Adaptation**
   - Monitoring and status JSON provide live feedback.
   - Activity feed (from `ops/events.jsonl`) will show how the system evolves over time.

4. **Self-Optimization**
   - CI/CD workflows can be tuned based on performance and stability signals.
   - Future agents can adjust schedules, thresholds and policies automatically.

5. **Self-Determination (Roadmap)**
   - GEORGE + Knowledge + CDT will allow the system to:
     - reason about its own roadmap,
     - propose improvements,
     - and plan multi-step modifications.

---

## 6. Roadmap: RAG, CDT and Beyond

This document is part of **Phase 1** of the Memory Layer.

Next planned evolutions:

1. **RAG Knowledge Layer (Phase 2)**
   - Add more documents under `memory/documents/`
     - e.g. `agent_roster.md`, `guardian_design.md`, `george_orchestrator.md`.
   - Implement embedding workflows and retrieval endpoints.
   - Expose internal knowledge for diagnostics and external demos.

2. **Cognitive Digital Twin (CDT) (Phase 3)**
   - Represent virtauto.OS as a **Cognitive Digital Twin**:
     - long-term intent,
     - system-level goals,
     - memory of all important transitions and releases.
   - Connect RAG knowledge with live telemetry and history.

3. **Industrial MAS Extension (Phase 4)**
   - Use virtauto.OS as blueprint for industrial Multi-Agent Systems:
     - production, supply chain, quality, maintenance, energy.
   - Reuse GEORGE and the self-agents as templates for factory-scale systems.

---

## 7. Intended Use of This Document

This document is written primarily for:

- internal agents (RAG / Knowledge / GEORGE),
- human developers working on virtauto.OS,
- future demos explaining how an Agentic Website is built.

It should be kept **up to date** whenever:

- new agents are added,
- major workflows are created or removed,
- the architecture evolves (especially RAG and CDT layers),
- new capabilities in Self-X behaviour are introduced.

> **Rule for future agents:**  
> If you significantly change the architecture of virtauto.OS, update this document and create a corresponding event in `/ops/events.jsonl`.
