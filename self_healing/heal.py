#!/usr/bin/env python3
"""
Phase 9 — Self-Healing (Adaptive Systems v1)
Scope: Regression-Recovery only · PR-only · deterministic · governed

This script:
- Runs deterministic detectors (R3 -> R2 -> R1)
- If regression found: applies a known playbook (creates minimal valid placeholders/templates)
- Writes a SELF_HEALING decision trace entry (JSONL)
- Emits GitHub Actions outputs for PR creation (no auto-merge, no direct main writes)

IMPORTANT:
- This script NEVER pushes to main.
- It only modifies the working tree. PR creation is done by workflow (e.g. peter-evans/create-pull-request).
"""

from __future__ import annotations

import json
import os
import sys
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Set


# -----------------------------
# Paths (repo-concrete defaults)
# -----------------------------
REPO_ROOT = Path(__file__).resolve().parents[1]

OPS_DIR = REPO_ROOT / "ops"
OPS_REPORTS_DIR = OPS_DIR / "reports"
DECISIONS_DIR = OPS_DIR / "decisions"

DECISION_TRACE_JSONL = OPS_REPORTS_DIR / "decision_trace.jsonl"

# R4: conflict-free append-only trace for self-healing (separate file)
SELF_HEALING_TRACE_JSONL = OPS_REPORTS_DIR / "self_healing_trace.jsonl"

# Phase-9 mandatory artifacts (R3)
DEFAULT_MANDATORY_ARTIFACTS = [
    # decision trace (JSONL)
    str(OPS_REPORTS_DIR / "decision_trace.jsonl"),
    # gate result
    str(DECISIONS_DIR / "gate_result.json"),
    # system status truth
    str(OPS_REPORTS_DIR / "system_status.json"),
    # latest pointer/summary
    str(OPS_REPORTS_DIR / "latest.json"),
]

# Optional manifest override (if you create it later)
MANIFEST_PATH = REPO_ROOT / "self_healing" / "templates" / "artifact_manifest.json"

# R1 concrete paths
CAPABILITY_GRAPH_PATH = REPO_ROOT / "governance" / "resilience" / "capability_graph.json"
CAPABILITY_PROFILES_PATH = OPS_DIR / "capability_profiles.json"

# R2 concrete path(s)
SYSTEM_STATUS_PATH = OPS_REPORTS_DIR / "system_status.json"
VALIDATE_STATUS_SCRIPT = OPS_DIR / "validate_status.py"


# -----------------------------
# Utilities
# -----------------------------
def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def append_jsonl(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, separators=(",", ":"), sort_keys=True) + "\n")


def gh_set_output(key: str, value: str) -> None:
    """
    Writes outputs for GitHub Actions.

    IMPORTANT: Multi-line values MUST use the heredoc format, otherwise
    GitHub will throw 'Unable to process file command output' / 'Invalid format'.
    """
    out = os.environ.get("GITHUB_OUTPUT")
    if not out:
        return

    # Use heredoc always (safe & simple)
    delim = "EOF_SELF_HEALING_OUTPUT"
    with open(out, "a", encoding="utf-8") as f:
        f.write(f"{key}<<{delim}\n")
        f.write(value)
        if not value.endswith("\n"):
            f.write("\n")
        f.write(f"{delim}\n")


def safe_rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except Exception:
        return str(path)


def is_valid_json_file(path: Path) -> bool:
    try:
        _ = read_json(path)
        return True
    except Exception:
        return False


def load_mandatory_artifacts() -> List[str]:
    """
    Allows you to override mandatory artifact list via templates/artifact_manifest.json later.
    """
    if MANIFEST_PATH.exists():
        try:
            manifest = read_json(MANIFEST_PATH)
            items = manifest.get("mandatory_artifacts", [])
            if isinstance(items, list) and all(isinstance(x, str) for x in items) and items:
                return items
        except Exception:
            # fall back to defaults deterministically
            pass
    return DEFAULT_MANDATORY_ARTIFACTS


# R5: deterministic cleanup to avoid PR noise (egg-info, caches, pyc)
def cleanup_non_governed_noise() -> None:
    """
    Removes known, deterministic build/cache artifacts that must never end up in governed PRs.
    Safe to call in CI; ignores errors.
    """
    # 1) Remove any *.egg-info directories anywhere
    try:
        for p in REPO_ROOT.rglob("*.egg-info"):
            if p.is_dir():
                shutil.rmtree(p, ignore_errors=True)
            elif p.is_file():
                try:
                    p.unlink(missing_ok=True)
                except Exception:
                    pass
    except Exception:
        pass

    # 2) Remove cache dirs anywhere
    for name in ("__pycache__", ".pytest_cache", ".mypy_cache"):
        try:
            for d in REPO_ROOT.rglob(name):
                if d.is_dir():
                    shutil.rmtree(d, ignore_errors=True)
        except Exception:
            pass

    # 3) Remove *.pyc anywhere
    try:
        for f in REPO_ROOT.rglob("*.pyc"):
            if f.is_file():
                try:
                    f.unlink(missing_ok=True)
                except Exception:
                    pass
    except Exception:
        pass


def _truncate(s: str, n: int = 4000) -> str:
    s = s or ""
    if len(s) <= n:
        return s
    return s[:n] + "\n...<truncated>...\n"


# -----------------------------
# Detector outputs
# -----------------------------
@dataclass(frozen=True)
class DetectorResult:
    regression: bool
    regression_id: Optional[str]
    type: Optional[str]
    severity: Optional[str]
    details: Dict[str, Any]


# -----------------------------
# R3 — Mandatory artifact missing
# -----------------------------
def detect_r3_missing_artifacts() -> DetectorResult:
    required = [Path(p) for p in load_mandatory_artifacts()]
    missing: List[str] = []
    for p in required:
        if not p.exists():
            missing.append(safe_rel(p))

    if missing:
        return DetectorResult(
            regression=True,
            regression_id="R3",
            type="MISSING_ARTIFACT",
            severity="blocking",
            details={"missing": missing, "required": [safe_rel(p) for p in required]},
        )

    return DetectorResult(
        regression=False,
        regression_id=None,
        type=None,
        severity=None,
        details={"required": [safe_rel(p) for p in required]},
    )


# -----------------------------
# R2 — Status validation fails
# Deterministic check: call ops/validate_status.py if present (exitcode != 0 => regression)
# Fallback: file exists + JSON + minimal required keys
# -----------------------------
def detect_r2_status_invalid() -> DetectorResult:
    # 1) If we have a deterministic validator script, use it as source of truth.
    if VALIDATE_STATUS_SCRIPT.exists() and VALIDATE_STATUS_SCRIPT.is_file():
        try:
            proc = subprocess.run(
                [sys.executable, str(VALIDATE_STATUS_SCRIPT)],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
            )
            if proc.returncode != 0:
                return DetectorResult(
                    regression=True,
                    regression_id="R2",
                    type="STATUS_INVALID",
                    severity="blocking",
                    details={
                        "reason": "ops/validate_status.py failed",
                        "exit_code": proc.returncode,
                        "stdout": _truncate(proc.stdout),
                        "stderr": _truncate(proc.stderr),
                        "validator": safe_rel(VALIDATE_STATUS_SCRIPT),
                    },
                )
            return DetectorResult(
                regression=False,
                regression_id=None,
                type=None,
                severity=None,
                details={
                    "validator": safe_rel(VALIDATE_STATUS_SCRIPT),
                    "exit_code": proc.returncode,
                },
            )
        except Exception as e:
            # Deterministic fallback: do NOT crash; report as regression with reason.
            return DetectorResult(
                regression=True,
                regression_id="R2",
                type="STATUS_INVALID",
                severity="blocking",
                details={
                    "reason": "validator execution error",
                    "validator": safe_rel(VALIDATE_STATUS_SCRIPT),
                    "error": str(e),
                },
            )

    # 2) Fallback (deterministic, minimal)
    path = SYSTEM_STATUS_PATH
    if not path.exists():
        return DetectorResult(
            regression=True,
            regression_id="R2",
            type="STATUS_INVALID",
            severity="blocking",
            details={"reason": "system_status.json missing", "path": safe_rel(path)},
        )

    if not is_valid_json_file(path):
        return DetectorResult(
            regression=True,
            regression_id="R2",
            type="STATUS_INVALID",
            severity="blocking",
            details={"reason": "system_status.json is not valid JSON", "path": safe_rel(path)},
        )

    data = read_json(path)
    required_top = ["generated_at", "environment"]
    missing = [k for k in required_top if k not in data]
    if missing:
        return DetectorResult(
            regression=True,
            regression_id="R2",
            type="STATUS_INVALID",
            severity="blocking",
            details={"reason": "missing required fields", "missing": missing, "path": safe_rel(path)},
        )

    if not isinstance(data.get("generated_at"), str) or not isinstance(data.get("environment"), str):
        return DetectorResult(
            regression=True,
            regression_id="R2",
            type="STATUS_INVALID",
            severity="blocking",
            details={"reason": "field type mismatch", "path": safe_rel(path)},
        )

    return DetectorResult(
        regression=False,
        regression_id=None,
        type=None,
        severity=None,
        details={"path": safe_rel(path), "validator": "fallback_minimal"},
    )


# -----------------------------
# R1 — Capability graph invalid
# Deterministic checks:
# - file exists + JSON parses
# - nodes schema (minimal): dict with "nodes": [ {id, primary?, depends_on?} ]
# - exactly one primary (determinism)
# - references: depends_on must point to known node ids
# - cycle detection (no cycles)
# - reference validation against ops/capability_profiles.json (known capability IDs)
# -----------------------------
def _extract_profile_ids(profiles: Any) -> Set[str]:
    """
    Deterministically extracts known capability IDs from ops/capability_profiles.json.
    Supports multiple stable shapes without guessing:
    - { "capabilities": [ {"id": "x"}, ... ] }
    - { "profiles": [ {"id": "x"}, ... ] }
    - [ {"id": "x"}, ... ]
    - { "x": {...}, "y": {...} }  (keys as ids)
    """
    ids: Set[str] = set()

    if isinstance(profiles, dict):
        if "capabilities" in profiles and isinstance(profiles["capabilities"], list):
            for item in profiles["capabilities"]:
                if isinstance(item, dict) and isinstance(item.get("id"), str) and item["id"].strip():
                    ids.add(item["id"].strip())
        if "profiles" in profiles and isinstance(profiles["profiles"], list):
            for item in profiles["profiles"]:
                if isinstance(item, dict) and isinstance(item.get("id"), str) and item["id"].strip():
                    ids.add(item["id"].strip())
        # keys-as-ids fallback (only if it looks like an id-map)
        for k, v in profiles.items():
            if isinstance(k, str) and k.strip() and isinstance(v, (dict, list)):
                ids.add(k.strip())

    elif isinstance(profiles, list):
        for item in profiles:
            if isinstance(item, dict) and isinstance(item.get("id"), str) and item["id"].strip():
                ids.add(item["id"].strip())

    return ids


def _detect_cycles(edges: Dict[str, List[str]]) -> List[List[str]]:
    """
    Returns list of cycles (each as path) deterministically.
    """
    visited: Set[str] = set()
    stack: Set[str] = set()
    parent: Dict[str, str] = {}
    cycles: List[List[str]] = []

    def dfs(u: str) -> None:
        visited.add(u)
        stack.add(u)
        for v in edges.get(u, []):
            if v not in visited:
                parent[v] = u
                dfs(v)
            elif v in stack:
                # found cycle u -> ... -> v
                cycle = [v]
                cur = u
                while cur != v and cur in parent:
                    cycle.append(cur)
                    cur = parent[cur]
                cycle.append(v)
                cycle.reverse()
                cycles.append(cycle)
        stack.remove(u)

    for node in sorted(edges.keys()):
        if node not in visited:
            dfs(node)

    # deterministic normalization: sort cycles by their string repr
    cycles_sorted = sorted(cycles, key=lambda c: "->".join(c))
    return cycles_sorted


def detect_r1_capability_graph_invalid() -> DetectorResult:
    path = CAPABILITY_GRAPH_PATH

    if not path.exists():
        return DetectorResult(
            regression=True,
            regression_id="R1",
            type="CAPABILITY_GRAPH_INVALID",
            severity="blocking",
            details={"reason": "capability_graph.json missing", "path": safe_rel(path)},
        )

    if not is_valid_json_file(path):
        return DetectorResult(
            regression=True,
            regression_id="R1",
            type="CAPABILITY_GRAPH_INVALID",
            severity="blocking",
            details={"reason": "capability_graph.json is not valid JSON", "path": safe_rel(path)},
        )

    graph = read_json(path)

    # minimal supported schema: {"nodes": [ ... ]}
    if not isinstance(graph, dict) or "nodes" not in graph or not isinstance(graph["nodes"], list):
        return DetectorResult(
            regression=True,
            regression_id="R1",
            type="CAPABILITY_GRAPH_INVALID",
            severity="blocking",
            details={
                "reason": "unsupported schema: expected object with 'nodes' list",
                "path": safe_rel(path),
            },
        )

    nodes_raw = graph["nodes"]
    nodes: List[Dict[str, Any]] = []
    for idx, n in enumerate(nodes_raw):
        if not isinstance(n, dict):
            return DetectorResult(
                regression=True,
                regression_id="R1",
                type="CAPABILITY_GRAPH_INVALID",
                severity="blocking",
                details={"reason": "node not an object", "index": idx, "path": safe_rel(path)},
            )
        nodes.append(n)

    # Collect IDs and validate uniqueness
    ids: List[str] = []
    for idx, n in enumerate(nodes):
        nid = n.get("id")
        if not isinstance(nid, str) or not nid.strip():
            return DetectorResult(
                regression=True,
                regression_id="R1",
                type="CAPABILITY_GRAPH_INVALID",
                severity="blocking",
                details={"reason": "node.id missing/invalid", "index": idx, "path": safe_rel(path)},
            )
        ids.append(nid.strip())

    dupes = sorted({x for x in ids if ids.count(x) > 1})
    if dupes:
        return DetectorResult(
            regression=True,
            regression_id="R1",
            type="CAPABILITY_GRAPH_INVALID",
            severity="blocking",
            details={"reason": "duplicate node ids", "duplicates": dupes, "path": safe_rel(path)},
        )

    id_set = set(ids)

    # Exactly one primary
    primaries = 0
    primary_ids: List[str] = []
    for nid, n in zip(ids, nodes):
        if n.get("primary") is True:
            primaries += 1
            primary_ids.append(nid)

    if primaries != 1:
        return DetectorResult(
            regression=True,
            regression_id="R1",
            type="CAPABILITY_GRAPH_INVALID",
            severity="blocking",
            details={
                "reason": "determinism rule violated (exactly 1 primary)",
                "primary_count": primaries,
                "primary_ids": primary_ids,
                "path": safe_rel(path),
            },
        )

    # Build edges from depends_on
    edges: Dict[str, List[str]] = {}
    bad_refs: Dict[str, List[str]] = {}
    bad_depends_type: List[str] = []

    for nid, n in zip(ids, nodes):
        deps = n.get("depends_on", [])
        if deps is None:
            deps = []
        if not isinstance(deps, list) or not all(isinstance(x, str) for x in deps):
            bad_depends_type.append(nid)
            deps = []
        deps_clean = [d.strip() for d in deps if isinstance(d, str) and d.strip()]
        edges[nid] = deps_clean

        unknown = [d for d in deps_clean if d not in id_set]
        if unknown:
            bad_refs[nid] = unknown

    if bad_depends_type:
        return DetectorResult(
            regression=True,
            regression_id="R1",
            type="CAPABILITY_GRAPH_INVALID",
            severity="blocking",
            details={
                "reason": "depends_on must be a list of strings",
                "nodes": sorted(bad_depends_type),
                "path": safe_rel(path),
            },
        )

    if bad_refs:
        return DetectorResult(
            regression=True,
            regression_id="R1",
            type="CAPABILITY_GRAPH_INVALID",
            severity="blocking",
            details={
                "reason": "invalid references in depends_on (unknown node ids)",
                "bad_refs": bad_refs,
                "path": safe_rel(path),
            },
        )

    # Cycle detection
    cycles = _detect_cycles(edges)
    if cycles:
        return DetectorResult(
            regression=True,
            regression_id="R1",
            type="CAPABILITY_GRAPH_INVALID",
            severity="blocking",
            details={
                "reason": "cycle detected in capability graph",
                "cycles": cycles,
                "path": safe_rel(path),
            },
        )

    # Reference validation against capability_profiles.json
    if not CAPABILITY_PROFILES_PATH.exists():
        return DetectorResult(
            regression=True,
            regression_id="R1",
            type="CAPABILITY_GRAPH_INVALID",
            severity="blocking",
            details={
                "reason": "capability_profiles.json missing (reference validation required)",
                "profiles_path": safe_rel(CAPABILITY_PROFILES_PATH),
                "path": safe_rel(path),
            },
        )

    if not is_valid_json_file(CAPABILITY_PROFILES_PATH):
        return DetectorResult(
            regression=True,
            regression_id="R1",
            type="CAPABILITY_GRAPH_INVALID",
            severity="blocking",
            details={
                "reason": "capability_profiles.json is not valid JSON",
                "profiles_path": safe_rel(CAPABILITY_PROFILES_PATH),
                "path": safe_rel(path),
            },
        )

    profiles = read_json(CAPABILITY_PROFILES_PATH)
    known_ids = _extract_profile_ids(profiles)
    if not known_ids:
        return DetectorResult(
            regression=True,
            regression_id="R1",
            type="CAPABILITY_GRAPH_INVALID",
            severity="blocking",
            details={
                "reason": "capability_profiles.json contains no extractable ids",
                "profiles_path": safe_rel(CAPABILITY_PROFILES_PATH),
                "path": safe_rel(path),
            },
        )

    unknown_in_graph = sorted([nid for nid in ids if nid not in known_ids])
    if unknown_in_graph:
        return DetectorResult(
            regression=True,
            regression_id="R1",
            type="CAPABILITY_GRAPH_INVALID",
            severity="blocking",
            details={
                "reason": "graph contains unknown capability ids (not in capability_profiles.json)",
                "unknown_ids": unknown_in_graph,
                "profiles_path": safe_rel(CAPABILITY_PROFILES_PATH),
                "path": safe_rel(path),
            },
        )

    return DetectorResult(
        regression=False,
        regression_id=None,
        type=None,
        severity=None,
        details={
            "path": safe_rel(path),
            "primary_id": primary_ids[0] if primary_ids else None,
            "node_count": len(ids),
            "profiles_path": safe_rel(CAPABILITY_PROFILES_PATH),
        },
    )


# -----------------------------
# Playbooks (known repair paths)
# -----------------------------
def playbook_r3_restore_missing_artifacts(det: DetectorResult) -> List[str]:
    changed: List[str] = []
    now = utc_now_iso()

    missing = det.details.get("missing", [])
    missing_set = set(str(x) for x in missing)

    p_trace = DECISION_TRACE_JSONL
    if safe_rel(p_trace) in missing_set:
        p_trace.parent.mkdir(parents=True, exist_ok=True)
        p_trace.write_text("", encoding="utf-8")
        changed.append(safe_rel(p_trace))

    p_gate = DECISIONS_DIR / "gate_result.json"
    if safe_rel(p_gate) in missing_set:
        write_json(
            p_gate,
            {
                "verdict": "UNKNOWN",
                "reason": "placeholder created by self-healing (R3)",
                "timestamp": now,
            },
        )
        changed.append(safe_rel(p_gate))

    p_status = OPS_REPORTS_DIR / "system_status.json"
    if safe_rel(p_status) in missing_set:
        write_json(
            p_status,
            {
                "generated_at": now,
                "environment": "production",
                "system": {"state": "UNKNOWN", "mode": "SUPERVISED"},
                "health": {"signal": "YELLOW", "overall_score": 0},
                "agents": {},
                "links": {
                    "decision_trace_jsonl": "ops/reports/decision_trace.jsonl",
                    "gate_result": "ops/decisions/gate_result.json",
                    "latest": "ops/reports/latest.json",
                },
            },
        )
        changed.append(safe_rel(p_status))

    p_latest = OPS_REPORTS_DIR / "latest.json"
    if safe_rel(p_latest) in missing_set:
        write_json(
            p_latest,
            {
                "generated_at": now,
                "environment": "production",
                "artifacts": {
                    "system_status": "ops/reports/system_status.json",
                    "decision_trace_jsonl": "ops/reports/decision_trace.jsonl",
                    "gate_result": "ops/decisions/gate_result.json",
                },
                "note": "placeholder created by self-healing (R3).",
            },
        )
        changed.append(safe_rel(p_latest))

    return changed


def playbook_r2_restore_status_template(det: DetectorResult) -> List[str]:
    now = utc_now_iso()
    p_status = OPS_REPORTS_DIR / "system_status.json"
    write_json(
        p_status,
        {
            "generated_at": now,
            "environment": "production",
            "system": {"state": "DEGRADED", "mode": "SUPERVISED"},
            "health": {"signal": "YELLOW", "overall_score": 0},
            "agents": {},
            "links": {
                "decision_trace_jsonl": "ops/reports/decision_trace.jsonl",
                "gate_result": "ops/decisions/gate_result.json",
                "latest": "ops/reports/latest.json",
            },
            "self_healing": {"regression": "R2", "reason": det.details.get("reason", "status invalid")},
        },
    )
    return [safe_rel(p_status)]


def playbook_r1_restore_capability_graph(det: DetectorResult) -> List[str]:
    now = utc_now_iso()
    p_graph = CAPABILITY_GRAPH_PATH
    p_graph.parent.mkdir(parents=True, exist_ok=True)

    template = {
        "version": 1,
        "generated_at": now,
        "nodes": [
            {"id": "core", "label": "Core", "primary": True, "depends_on": []},
        ],
        "note": "template restored by self-healing (R1).",
    }
    write_json(p_graph, template)
    return [safe_rel(p_graph)]


# -----------------------------
# Decision Trace (enforced)
# -----------------------------
_REQUIRED_TRACE_KEYS = {
    "decision_type": str,
    "regression_id": (str, type(None)),
    "detector": (str, type(None)),
    "playbook": str,
    "action": str,
    "authority": str,
    "result": str,
    "timestamp": str,
    "details": dict,
}


def _validate_trace_entry(entry: Dict[str, Any]) -> Tuple[bool, str]:
    for k, t in _REQUIRED_TRACE_KEYS.items():
        if k not in entry:
            return False, f"missing key: {k}"
        if not isinstance(entry[k], t):
            return False, f"type mismatch for {k}: expected {t}, got {type(entry[k])}"
    if entry.get("decision_type") != "SELF_HEALING":
        return False, "decision_type must be SELF_HEALING"
    if entry.get("action") != "OPEN_PR":
        return False, "action must be OPEN_PR"
    if entry.get("result") != "ESCALATED_TO_HUMAN":
        return False, "result must be ESCALATED_TO_HUMAN"
    return True, "ok"


def write_self_healing_trace(det: DetectorResult, playbook: str, pr_branch: str, changed_files: List[str]) -> None:
    entry = {
        "decision_type": "SELF_HEALING",
        "regression_id": det.regression_id,
        "detector": det.type,
        "playbook": playbook,
        "action": "OPEN_PR",
        "authority": "SYSTEM",
        "result": "ESCALATED_TO_HUMAN",
        "timestamp": utc_now_iso(),
        "details": {
            "severity": det.severity,
            "detector_output": det.details,
            "branch": pr_branch,
            "changed_files": changed_files,
        },
    }

    ok, reason = _validate_trace_entry(entry)
    if not ok:
        # deterministic refusal to write invalid trace
        raise RuntimeError(f"invalid self-healing trace entry: {reason}")

    # R4: write into self_healing_trace.jsonl (conflict-free append-only)
    append_jsonl(SELF_HEALING_TRACE_JSONL, entry)


# -----------------------------
# Orchestration
# -----------------------------
def pick_regression() -> DetectorResult:
    for fn in (detect_r3_missing_artifacts, detect_r2_status_invalid, detect_r1_capability_graph_invalid):
        res = fn()
        if res.regression:
            return res
    return DetectorResult(False, None, None, None, {"note": "no regression"})


def build_pr_metadata(det: DetectorResult) -> Tuple[str, str, str]:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    rid = det.regression_id or "RX"
    branch = f"self-heal/{ts}-{rid}"

    title_map = {
        "R3": "Self-Healing PR (R3): Missing mandatory artifact(s)",
        "R2": "Self-Healing PR (R2): Status validation failed",
        "R1": "Self-Healing PR (R1): Capability graph invalid",
    }
    title = title_map.get(rid, f"Self-Healing PR ({rid}): Regression detected")

    body = (
        "## Self-Healing (Phase 9)\n\n"
        f"**Regression:** {rid} · {det.type}\n"
        f"**Severity:** {det.severity}\n\n"
        "### Detector Output (machine-readable)\n"
        f"```json\n{json.dumps(det.details, indent=2, sort_keys=True)}\n```\n\n"
        "### Governance\n"
        "- PR-only: ✅ (no direct write to `main`)\n"
        "- Deterministic: ✅ (known playbooks only)\n"
        "- Decision-traced: ✅ (`ops/reports/self_healing_trace.jsonl`)\n"
    )
    return branch, title, body


def main() -> int:
    det = pick_regression()

    if not det.regression:
        print("No regression detected. noop.")
        gh_set_output("regression", "false")
        gh_set_output("regression_id", "")
        gh_set_output("pr_branch", "")
        gh_set_output("pr_title", "")
        gh_set_output("pr_body", "")
        gh_set_output("changed_files", "")
        return 0

    pr_branch, pr_title, pr_body = build_pr_metadata(det)

    changed: List[str] = []
    playbook_name = ""

    if det.regression_id == "R3":
        playbook_name = "restore_missing_artifacts"
        changed = playbook_r3_restore_missing_artifacts(det)
    elif det.regression_id == "R2":
        playbook_name = "restore_status_template"
        changed = playbook_r2_restore_status_template(det)
    elif det.regression_id == "R1":
        playbook_name = "restore_capability_graph"
        changed = playbook_r1_restore_capability_graph(det)
    else:
        print(f"Unknown regression_id={det.regression_id}. Refusing to act.")
        gh_set_output("regression", "true")
        gh_set_output("regression_id", det.regression_id or "")
        gh_set_output("pr_branch", pr_branch)
        gh_set_output("pr_title", pr_title)
        gh_set_output("pr_body", pr_body)
        gh_set_output("changed_files", "")
        return 2

    # Trace must be valid & append-only
    write_self_healing_trace(det, playbook_name, pr_branch, changed)

    # R5: cleanup non-governed noise deterministically (prevents egg-info, pyc, caches)
    cleanup_non_governed_noise()

    gh_set_output("regression", "true")
    gh_set_output("regression_id", det.regression_id or "")
    gh_set_output("pr_branch", pr_branch)
    gh_set_output("pr_title", pr_title)
    gh_set_output("pr_body", pr_body)
    gh_set_output("changed_files", ",".join(changed))

    print(f"Regression detected: {det.regression_id} · {det.type}")
    print(f"Playbook: {playbook_name}")
    print(f"Proposed branch: {pr_branch}")
    print(f"Changed files: {changed}")
    return 0


if __name__ == "__main__":
    sys.exit(main())