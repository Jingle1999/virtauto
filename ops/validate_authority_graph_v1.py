#!/usr/bin/env python3
"""
Authority Graph Validator (v1) — WARN-only (non-fatal)

Purpose:
- Provide deterministic, dependency-free validation for ops/authority_graph_v1.yaml
- Emits VALIDATION WARN messages for missing/invalid structure
- Exits 0 always (Phase 10 preparation: visibility first, enforcement later)

Rules (minimal, stable):
- File must exist and be non-empty
- Must include top-level markers: version:, nodes:, edges:
- Extract node ids (best-effort) and edge pairs (best-effort)
- Warn if required canonical nodes are missing
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import List, Set, Tuple


AUTH_GRAPH_PATH = Path("ops/authority_graph_v1.yaml")

RE_NODE_ID = re.compile(r"^\s*-\s*id:\s*([A-Za-z0-9_\-\.]+)\s*$")
RE_EDGE_FROM = re.compile(r"^\s*-\s*from:\s*([A-Za-z0-9_\-\.]+)\s*$")
RE_EDGE_TO = re.compile(r"^\s*to:\s*([A-Za-z0-9_\-\.]+)\s*$")


def warn(msg: str) -> None:
    print(f"VALIDATION WARN: {msg}")


def _has_marker(text: str, marker: str) -> bool:
    # marker expected like "nodes:" or "version:"
    return any(line.strip().startswith(marker) for line in text.splitlines())


def parse_nodes_and_edges(text: str) -> Tuple[Set[str], List[Tuple[str, str]]]:
    """
    Best-effort parse:
    - nodes: look for '- id: X'
    - edges: look for '- from: A' followed by 'to: B' (next lines)
    """
    nodes: Set[str] = set()
    edges: List[Tuple[str, str]] = []

    lines = text.splitlines()
    pending_from: str | None = None

    for line in lines:
        m_id = RE_NODE_ID.match(line)
        if m_id:
            nodes.add(m_id.group(1))
            continue

        m_from = RE_EDGE_FROM.match(line)
        if m_from:
            pending_from = m_from.group(1)
            continue

        m_to = RE_EDGE_TO.match(line)
        if m_to and pending_from:
            edges.append((pending_from, m_to.group(1)))
            pending_from = None
            continue

    return nodes, edges


def main() -> int:
    if not AUTH_GRAPH_PATH.exists():
        warn(f"{AUTH_GRAPH_PATH} not found (authority graph evidence missing).")
        return 0

    text = AUTH_GRAPH_PATH.read_text(encoding="utf-8", errors="replace").strip()
    if not text:
        warn(f"{AUTH_GRAPH_PATH} is empty.")
        return 0

    # Minimal structure markers
    for marker in ("version:", "nodes:", "edges:"):
        if not _has_marker(text, marker):
            warn(f"{AUTH_GRAPH_PATH} missing marker '{marker}' (expected YAML section).")

    nodes, edges = parse_nodes_and_edges(text)

    if not nodes:
        warn(f"{AUTH_GRAPH_PATH} contains no parseable node ids (expected '- id: <node>').")
    if not edges:
        warn(f"{AUTH_GRAPH_PATH} contains no parseable edges (expected '- from:' + 'to:').")

    # Canonical nodes we expect to exist for Phase 10 prep (adjust later if you rename)
    required_nodes = {"george", "repo_owner", "human_reviewer", "system"}
    missing = sorted(n for n in required_nodes if n not in nodes)

    if missing:
        warn(
            f"{AUTH_GRAPH_PATH} missing canonical nodes: {', '.join(missing)} "
            f"(present: {', '.join(sorted(nodes)) if nodes else '—'})"
        )

    # Basic sanity: edge endpoints should exist
    if nodes and edges:
        bad_edges = [(a, b) for (a, b) in edges if a not in nodes or b not in nodes]
        if bad_edges:
            sample = ", ".join([f"{a}->{b}" for a, b in bad_edges[:5]])
            warn(f"{AUTH_GRAPH_PATH} has edges referencing unknown nodes (sample): {sample}")

    print("VALIDATION OK: authority_graph_v1.yaml checked (WARN-only mode).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())