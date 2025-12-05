---
id: docs-003
title: "GEORGE Orchestrator — Rules & Intent Layer"
version: "1.0"
type: "rag-doc"
description: "Foundational rule set, orchestration logic, and intent-routing model for GEORGE — the central brain of virtauto.OS."
---

# GEORGE Orchestrator — Rules & Intent Model (V1.0)

## Purpose
GEORGE is the central orchestration layer of virtauto.OS.  
It determines:
- which agent should act
- when an agent is allowed to act
- how conflicting actions are resolved
- how global system intent is preserved
- how autonomy evolves over time

This document provides the initial rule set + decision model for the orchestrator.

---

# 1. Core Responsibilities

## 1.1 Intent Routing
GEORGE assigns intent categories:
- **security-intent** → Self-Guardian  
- **health-intent** → Self-Monitoring  
- **content-intent** → Self-Content  
- **deployment-intent** → Deploy Agent  
- **marketing-intent** → Content Agent (planned)  
- **strategy-intent** → CDT (future)

---

## 1.2 Rule-Based Agent Activation

GEORGE selects agents using decision rules:

### Rule A — Security First
