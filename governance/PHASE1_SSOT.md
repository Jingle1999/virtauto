# virtauto Phase 1 — Single Source of Truth (SSOT)

## Purpose

This document defines the operational Single Source of Truth (SSOT) for virtauto Phase 1.

Phase 1 establishes a **Decision Governance Proof of Concept** where governance artifacts are the system interface.

In Phase 1:

- Decisions are represented as artifacts
- Validation is represented as artifacts
- System status is represented as artifacts
- Audit is represented as artifacts

The repository becomes the operational governance surface.

---

# Phase 1 Operational SSOT

The following files are considered **authoritative system state** in Phase 1.

## Status Artifacts

These represent the current system state:

status/system_health.json
status/dashboard_summary.json
status/latest_decision.json

****


Purpose:

- System operational status
- Latest decision output
- Aggregated governance health

---

## Governance Artifacts

These represent decision governance:

governance/decision_traces/GEORGE-example.json
governance/validation/GUARDIAN-example.json


Purpose:

- Decision evidence
- Validation evidence

---

## Audit Artifact

audit/self_audit_report.json


Purpose:

- Governance completeness validation
- System self-check

---

# Phase 1 System Rule

The core governance rule for Phase 1:

**No change without governance evidence**

Every meaningful system change must result in:

- Decision Trace
- Validation Artifact
- Status Update
- Audit Report

---

# Non-SSOT / Legacy Paths

The following paths exist but are **not authoritative** in Phase 1:

## Legacy / Experimental

decision_traces/ (root level)
status/status.json
*.bak files
experimental pages
archive content


These files may exist for:

- experimentation
- migration
- historical reference

They are **not part of the operational SSOT**.

---

# Website as Governance Surface

The website reads from SSOT artifacts:

Status page reads:

- system_health.json
- latest_decision.json
- self_audit_report.json

This makes the website:

- System Interface
- Governance Viewer
- Decision Evidence Surface

---

# Phase 1 Boundary

Phase 1 does NOT include:

- Industrial connectors
- Real MES integration
- ERP integration
- Security layer
- Identity layer
- Decision signing

These belong to later phases.

---

# Phase 1 Summary

Phase 1 establishes:

- Decision artifacts
- Validation artifacts
- Status artifacts
- Audit artifacts
- Git-governed system state

This forms the foundation of the **Decision Governance Layer**.
