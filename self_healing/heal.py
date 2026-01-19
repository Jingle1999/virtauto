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
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# -----------------------------
# Paths (repo-concrete defaults)
# -----------------------------
REPO_ROOT = Path(__file__).resolve().parents[1]

OPS_DIR = REPO_ROOT / "ops"
OPS_REPORTS_DIR = OPS_DIR / "reports"
DECISIONS_DIR = OPS_DIR / "decisions"

DECISION_TRACE_JSONL = OPS_REPORTS_DIR / "decision_trace.jsonl"

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

    IMPORTANT:
    GitHub Actions requires multiline outputs to use the heredoc style:
      key<<DELIM
      <value>
      DELIM
    """
    out = os.environ.get("GITHUB_OUTPUT")
    if not out:
        return

    # Normalize value to string and ensure no None
    if value is None:
        value = ""

    value = str(value)

    # Use a unique delimiter to avoid collisions with content.
    delim = f"__GH_OUT_{key}_{uuid.uuid4().hex}__"

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
# (Deterministic check: file exists + JSON + minimal required keys)
# You can later harden this by calling ops/validate_status.py in the workflow.
# -----------------------------
def detect_r2_status_invalid() -> DetectorResult:
    path = OPS_REPORTS_DIR / "system_status.json"
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
    # Minimal truth requirements (keep minimal & deterministic)
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

    # Basic type sanity
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
        details={"path": safe_rel(path)},
    )


# -----------------------------
# R1 — Capability graph invalid
# Minimal deterministic checks (JSON parse + exactly one primary)
# You can later extend with schema/refs (against ops/capability_profiles.json).
# -----------------------------
def detect_r1_capability_graph_invalid() -> DetectorResult:
    path = REPO_ROOT / "governance" / "resilience" / "capability_graph.json"
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

    data = read_json(path)
    # Determinism rule: exactly 1 primary
    primaries = 0
    if isinstance(data, dict):
        nodes = data.get("nodes")
        if isinstance(nodes, list):
            for n in nodes:
                if isinstance(n, dict) and n.get("primary") is True:
                    primaries += 1
        else:
            for _, v in data.items():
                if isinstance(v, dict) and v.get("primary") is True:
                    primaries += 1
    elif isinstance(data, list):
        for n in data:
            if isinstance(n, dict) and n.get("primary") is True:
                primaries += 1

    if primaries != 1:
        return DetectorResult(
            regression=True,
            regression_id="R1",
            type="CAPABILITY_GRAPH_INVALID",
            severity="blocking",
            details={
                "reason": "determinism rule violated (exactly 1 primary)",
                "primary_count": primaries,
                "path": safe_rel(path),
            },
        )

    return DetectorResult(
        regression=False,
        regression_id=None,
        type=None,
        severity=None,
        details={"path": safe_rel(path), "primary_count": primaries},
    )


# -----------------------------
# Playbooks (known repair paths)
# -----------------------------
def playbook_r3_restore_missing_artifacts(det: DetectorResult) -> List[str]:
    """
    Creates minimal, valid placeholders for missing mandatory artifacts.
    """
    changed: List[str] = []
    now = utc_now_iso()

    missing = det.details.get("missing", [])
    missing_set = set(str(x) for x in missing)

    # decision_trace.jsonl: create if missing (empty JSONL is acceptable)
    p_trace = DECISION_TRACE_JSONL
    if safe_rel(p_trace) in missing_set:
        p_trace.parent.mkdir(parents=True, exist_ok=True)
        p_trace.write_text("", encoding="utf-8")
        changed.append(safe_rel(p_trace))

    # gate_result.json: minimal valid structure
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

    # system_status.json: minimal truth-locked status
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

    # latest.json: canonical pointer file
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
    """
    Restores a minimal valid status file (without guessing).
    """
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
    """
    Restores capability_graph.json from a deterministic minimal template.
    (No creative reconstruction.)
    """
    now = utc_now_iso()
    p_graph = REPO_ROOT / "governance" / "resilience" / "capability_graph.json"
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
# Decision Trace
# -----------------------------
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
    append_jsonl(DECISION_TRACE_JSONL, entry)


# -----------------------------
# Orchestration
# -----------------------------
def pick_regression() -> DetectorResult:
    """
    Deterministic order per plan:
    R3 -> R2 -> R1
    """
    for fn in (detect_r3_missing_artifacts, detect_r2_status_invalid, detect_r1_capability_graph_invalid):
        res = fn()
        if res.regression:
            return res
    return DetectorResult(False, None, None, None, {"note": "no regression"})


def build_pr_metadata(det: DetectorResult) -> Tuple[str, str, str]:
    """
    Returns (branch, title, body)
    Branch naming: self-heal/<timestamp>-<regression-id>
    """
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
        f"## Self-Healing (Phase 9)\n\n"
        f"**Regression:** {rid} · {det.type}\n"
        f"**Severity:** {det.severity}\n\n"
        f"### Detector Output (machine-readable)\n"
        f"```json\n{json.dumps(det.details, indent=2, sort_keys=True)}\n```\n\n"
        f"### Governance\n"
        f"- PR-only: ✅ (no direct write to `main`)\n"
        f"- Deterministic: ✅ (known playbooks only)\n"
        f"- Decision-traced: ✅ (`ops/reports/decision_trace.jsonl`)\n"
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

    write_self_healing_trace(det, playbook_name, pr_branch, changed)

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
