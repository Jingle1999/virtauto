#!/usr/bin/env python3
"""
Phase 9 — Self-Healing (Adaptive Systems v1)
Scope: Regression-Recovery only · PR-only · deterministic · governed

This script:
- Runs deterministic detectors (R3 -> R2 -> R0 -> R1)
- If regression found: applies a known playbook (creates minimal valid placeholders/templates OR proposal-only)
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

# Phase 9.2: recovery proposal artifact (must land in PR)
RECOVERY_PROPOSAL_MD = OPS_REPORTS_DIR / "recovery_proposal.md"


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


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


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


def _get(d: Any, path: List[str], default: Any = None) -> Any:
    """
    Safe nested getter for dicts.
    """
    cur = d
    for k in path:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


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
        details={"path": safe_rel(path)},
    )


# -----------------------------
# R0 — Health/Gate anomaly (Phase 9.2)
# Trigger conditions:
# - system_status.health.signal != GREEN
# - system_status.autonomy_score.gate_verdict == DENY
# - OR ops/decisions/gate_result.json verdict == DENY
# -----------------------------
def detect_r0_health_or_gate_anomaly() -> DetectorResult:
    status_path = OPS_REPORTS_DIR / "system_status.json"
    if not status_path.exists() or not is_valid_json_file(status_path):
        # Let R2 handle invalid status
        return DetectorResult(False, None, None, None, {"note": "status missing/invalid (handled by R2)"})

    status = read_json(status_path)

    health_signal = _get(status, ["health", "signal"], default=None)
    gate_verdict = _get(status, ["autonomy_score", "gate_verdict"], default=None)

    gate_path = DECISIONS_DIR / "gate_result.json"
    gate_result_verdict = None
    if gate_path.exists() and is_valid_json_file(gate_path):
        gate_obj = read_json(gate_path)
        if isinstance(gate_obj, dict):
            gate_result_verdict = gate_obj.get("verdict")

    anomalies: List[Dict[str, Any]] = []

    if isinstance(health_signal, str) and health_signal.upper() != "GREEN":
        anomalies.append(
            {
                "kind": "HEALTH_NOT_GREEN",
                "path": "health.signal",
                "value": health_signal,
                "expected": "GREEN",
            }
        )

    if isinstance(gate_verdict, str) and gate_verdict.upper() == "DENY":
        anomalies.append(
            {
                "kind": "GATE_DENY",
                "path": "autonomy_score.gate_verdict",
                "value": gate_verdict,
                "expected": "ALLOW",
            }
        )

    if isinstance(gate_result_verdict, str) and gate_result_verdict.upper() == "DENY":
        anomalies.append(
            {
                "kind": "GATE_DENY",
                "path": "ops/decisions/gate_result.json:verdict",
                "value": gate_result_verdict,
                "expected": "ALLOW",
            }
        )

    if not anomalies:
        return DetectorResult(False, None, None, None, {"note": "no health/gate anomaly"})

    return DetectorResult(
        regression=True,
        regression_id="R0",
        type="HEALTH_OR_GATE_ANOMALY",
        severity="blocking",
        details={
            "status_path": safe_rel(status_path),
            "gate_result_path": safe_rel(gate_path),
            "anomalies": anomalies,
            "observed": {
                "health_signal": health_signal,
                "autonomy_gate_verdict": gate_verdict,
                "gate_result_verdict": gate_result_verdict,
            },
        },
    )


# -----------------------------
# R1 — Capability graph invalid
# Minimal deterministic checks (JSON parse + exactly one primary)
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
# Recovery Proposal (Phase 9.2 artifact)
# -----------------------------
def render_recovery_proposal_md(det: DetectorResult, changed_files: List[str]) -> str:
    now = utc_now_iso()

    status_path = "ops/reports/system_status.json"
    gate_path = "ops/decisions/gate_result.json"
    trace_path = "ops/reports/self_healing_trace.jsonl"

    anomalies = det.details.get("anomalies", [])
    anomalies_md = ""
    if isinstance(anomalies, list) and anomalies:
        lines = []
        for a in anomalies:
            if isinstance(a, dict):
                kind = a.get("kind", "UNKNOWN")
                path = a.get("path", "?")
                val = a.get("value", None)
                exp = a.get("expected", None)
                lines.append(f"- **{kind}** at `{path}`: observed `{val}` (expected `{exp}`)")
        anomalies_md = "\n".join(lines)
    else:
        anomalies_md = "- (no anomaly details provided)"

    changed_md = "\n".join([f"- `{p}`" for p in changed_files]) if changed_files else "- (no files changed)"

    # Proposal is intentionally conservative: proposal-only, PR-based, human-decided.
    return (
        "# Recovery Proposal (Self-Healing v1)\n\n"
        f"**Timestamp (UTC):** `{now}`\n\n"
        "## Detected Condition\n\n"
        f"- **Regression ID:** `{det.regression_id}`\n"
        f"- **Type:** `{det.type}`\n"
        f"- **Severity:** `{det.severity}`\n\n"
        "### Anomalies\n\n"
        f"{anomalies_md}\n\n"
        "## Evidence\n\n"
        f"- System status: `{status_path}`\n"
        f"- Gate result: `{gate_path}`\n"
        f"- Self-healing trace: `{trace_path}`\n\n"
        "## Proposed Recovery (PR-only)\n\n"
        "This proposal does **not** execute changes autonomously.\n"
        "It creates a draft PR for **human governance** to review and decide.\n\n"
        "Recommended review checklist:\n"
        "1. Confirm the anomaly in `system_status.json` / `gate_result.json`.\n"
        "2. Inspect recent decision traces for root-cause signals.\n"
        "3. If `gate_verdict` is `DENY`, identify which rule/gate blocked and why.\n"
        "4. Approve the minimal fix PR only if it is deterministic and governed.\n\n"
        "## Files Included in This Proposal\n\n"
        f"{changed_md}\n"
    )


# -----------------------------
# Playbooks (known repair paths)
# -----------------------------
def playbook_r0_proposal_only(det: DetectorResult) -> List[str]:
    """
    Phase 9.2 minimal playbook: generate recovery_proposal.md as PR content.
    No direct operational changes beyond proposal artifact.
    """
    text = render_recovery_proposal_md(det, changed_files=[safe_rel(RECOVERY_PROPOSAL_MD)])
    write_text(RECOVERY_PROPOSAL_MD, text)
    return [safe_rel(RECOVERY_PROPOSAL_MD)]


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

    # Ensure proposal exists for governed review
    proposal = render_recovery_proposal_md(det, changed_files=changed + [safe_rel(RECOVERY_PROPOSAL_MD)])
    write_text(RECOVERY_PROPOSAL_MD, proposal)
    changed.append(safe_rel(RECOVERY_PROPOSAL_MD))

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

    changed = [safe_rel(p_status)]

    # Ensure proposal exists for governed review
    proposal = render_recovery_proposal_md(det, changed_files=changed + [safe_rel(RECOVERY_PROPOSAL_MD)])
    write_text(RECOVERY_PROPOSAL_MD, proposal)
    changed.append(safe_rel(RECOVERY_PROPOSAL_MD))

    return changed


def playbook_r1_restore_capability_graph(det: DetectorResult) -> List[str]:
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

    changed = [safe_rel(p_graph)]

    # Ensure proposal exists for governed review
    proposal = render_recovery_proposal_md(det, changed_files=changed + [safe_rel(RECOVERY_PROPOSAL_MD)])
    write_text(RECOVERY_PROPOSAL_MD, proposal)
    changed.append(safe_rel(RECOVERY_PROPOSAL_MD))

    return changed


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
    # R4: write into self_healing_trace.jsonl (conflict-free append-only)
    append_jsonl(SELF_HEALING_TRACE_JSONL, entry)


# -----------------------------
# Orchestration
# -----------------------------
def pick_regression() -> DetectorResult:
    # Keep ordering deterministic and aligned with Phase 9 triggers:
    # - R3: mandatory artifact missing (hard failure)
    # - R2: status invalid (hard failure)
    # - R0: health/gate anomaly (Phase 9.2)
    # - R1: capability graph invalid
    for fn in (
        detect_r3_missing_artifacts,
        detect_r2_status_invalid,
        detect_r0_health_or_gate_anomaly,
        detect_r1_capability_graph_invalid,
    ):
        res = fn()
        if res.regression:
            return res
    return DetectorResult(False, None, None, None, {"note": "no regression"})


def build_pr_metadata(det: DetectorResult) -> Tuple[str, str, str]:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    rid = det.regression_id or "RX"
    branch = f"self-heal/{ts}-{rid}"

    title_map = {
        "R0": "Self-Healing PR (R0): Health/Gate anomaly detected",
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
        "### Included Proposal\n"
        "- `ops/reports/recovery_proposal.md`\n\n"
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

    if det.regression_id == "R0":
        playbook_name = "proposal_only"
        changed = playbook_r0_proposal_only(det)
    elif det.regression_id == "R3":
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

# governace recheck

# governance re-evaluation trigger
