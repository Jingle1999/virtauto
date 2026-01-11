#!/usr/bin/env python3
# ops/guardian_agent.py
# Deterministic Guardian/Authority Agent (primary/backup).
# No learning. No heuristics. Policy-driven checks only.

from __future__ import annotations
import argparse
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Tuple

POLICY_PATH = Path("ops/guardian_policy.json")

TRACE_PATH = Path("ops/reports/guardian_trace.jsonl")
ACTIVITY_PATH = Path("ops/agent_activity.jsonl")
GOV_OUT_PATH = Path("ops/reports/governance_outputs.json")

def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def ensure_parent(p: Path) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)

def append_jsonl(path: Path, obj: dict) -> None:
    ensure_parent(path)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")

def write_json(path: Path, obj: dict) -> None:
    ensure_parent(path)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write("\n")
    tmp.replace(path)

def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")

def ci_contains(haystack: str, needle: str) -> bool:
    return needle.lower() in haystack.lower()

@dataclass
class Finding:
    severity: str  # "BLOCK" | "WARN"
    code: str
    message: str
    path: str | None = None

def load_policy() -> Dict[str, Any]:
    if not POLICY_PATH.exists():
        raise FileNotFoundError(f"Missing policy file: {POLICY_PATH}")
    return json.loads(POLICY_PATH.read_text(encoding="utf-8"))

def check_truth_files(policy: Dict[str, Any]) -> List[Finding]:
    findings: List[Finding] = []
    truth = policy.get("truth", {})
    required = truth.get("required_truth_paths", [])
    for p in required:
        pp = Path(p)
        if not pp.exists():
            findings.append(Finding(
                severity="BLOCK",
                code="TRUTH_MISSING",
                message=f"Required truth source missing: {p}",
                path=p
            ))
    return findings

def extract_status_truth_path(status_html: str) -> str | None:
    # Looks for: const TRUTH_PATH = "/ops/reports/system_status.json";
    m = re.search(r'const\s+TRUTH_PATH\s*=\s*"([^"]+)"\s*;', status_html)
    return m.group(1).strip() if m else None

def check_status_truth_lock(policy: Dict[str, Any]) -> List[Finding]:
    findings: List[Finding] = []
    truth = policy.get("truth", {})
    status_path = Path(truth.get("status_page_path", "status/index.html"))
    expected = truth.get("status_page_must_reference_truth_path")

    if not status_path.exists():
        findings.append(Finding(
            severity="BLOCK",
            code="STATUS_PAGE_MISSING",
            message=f"Status page not found at {status_path}",
            path=str(status_path)
        ))
        return findings

    html = read_text(status_path)
    found = extract_status_truth_path(html)

    if not found:
        findings.append(Finding(
            severity="BLOCK",
            code="TRUTH_PATH_NOT_FOUND",
            message="Status page does not declare TRUTH_PATH constant.",
            path=str(status_path)
        ))
        return findings

    if expected and found != expected:
        findings.append(Finding(
            severity="BLOCK",
            code="TRUTH_PATH_MISMATCH",
            message=f"Status page TRUTH_PATH mismatch. Found '{found}' but expected '{expected}'.",
            path=str(status_path)
        ))

    return findings

def check_messaging_controls(policy: Dict[str, Any]) -> List[Finding]:
    findings: List[Finding] = []
    mc = policy.get("messaging_controls", {})
    scan_paths = [Path(p) for p in mc.get("scan_paths", [])]

    avoid = mc.get("avoid_phrases_case_insensitive", [])
    require = mc.get("require_phrases_anywhere_case_insensitive", [])

    avoid_hits: List[Tuple[str, str]] = []
    require_hits = {r: False for r in require}

    for p in scan_paths:
        if not p.exists():
            # Not blocking: some pages may not exist in all builds
            findings.append(Finding(
                severity="WARN",
                code="SCAN_PATH_MISSING",
                message=f"Scan path not found (skipped): {p}",
                path=str(p)
            ))
            continue

        text = read_text(p)

        # avoid phrase scan
        for phrase in avoid:
            if ci_contains(text, phrase):
                avoid_hits.append((str(p), phrase))

        # require phrase scan
        for phrase in require:
            if not require_hits[phrase] and ci_contains(text, phrase):
                require_hits[phrase] = True

    # enforce avoid hits
    if avoid_hits:
        msg = "; ".join([f"{path} contains '{phrase}'" for path, phrase in avoid_hits[:12]])
        findings.append(Finding(
            severity="BLOCK",
            code="MESSAGING_AVOID_PHRASE",
            message=f"Forbidden marketing phrases detected: {msg}",
            path="multiple"
        ))

    # enforce require hits (optional)
    enforcement = policy.get("enforcement", {})
    if enforcement.get("block_on_missing_required_phrases", False):
        missing = [p for p, ok in require_hits.items() if not ok]
        if missing:
            findings.append(Finding(
                severity="BLOCK",
                code="MESSAGING_REQUIRED_MISSING",
                message=f"Required phrases missing across scanned pages: {', '.join(missing)}",
                path="multiple"
            ))

    return findings

def compute_verdict(findings: List[Finding]) -> str:
    return "BLOCK" if any(f.severity == "BLOCK" for f in findings) else "PASS"

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", choices=["primary", "backup"], required=True)
    ap.add_argument("--run-id", default=os.getenv("GITHUB_RUN_ID", "local"))
    ap.add_argument("--attempt", default=os.getenv("GITHUB_RUN_ATTEMPT", "0"))
    ap.add_argument("--sha", default=os.getenv("GITHUB_SHA", "local"))
    ap.add_argument("--ref", default=os.getenv("GITHUB_REF_NAME", "local"))
    args = ap.parse_args()

    ts = utc_now()
    agent_name = "guardian_agent_v1" if args.agent == "primary" else "guardian_agent_v1_backup"
    trace_id = f"{args.run_id}-{args.attempt}"

    policy = load_policy()

    findings: List[Finding] = []
    findings.extend(check_truth_files(policy))
    findings.extend(check_status_truth_lock(policy))
    findings.extend(check_messaging_controls(policy))

    verdict = compute_verdict(findings)

    # Public governance output (safe, non-sensitive)
    gov_out = {
        "generated_at": ts,
        "capability": "guardian_authority",
        "agent": agent_name,
        "trace_id": trace_id,
        "sha": args.sha,
        "ref": args.ref,
        "verdict": verdict,
        "findings": [
            {
                "severity": f.severity,
                "code": f.code,
                "message": f.message,
                "path": f.path
            } for f in findings
        ],
        "policy": {
            "policy_version": policy.get("policy_version", "unknown"),
            "mode": policy.get("mode", "SUPERVISED")
        }
    }

    # Evidence: always write outputs even if BLOCK, because it's auditable
    write_json(GOV_OUT_PATH, gov_out)

    trace_event = {
        "ts": ts,
        "capability": "guardian_authority",
        "event": "policy_evaluation",
        "trace_id": trace_id,
        "agent": agent_name,
        "result": verdict,
        "policy_version": policy.get("policy_version", "unknown"),
        "finding_count": len(findings)
    }
    append_jsonl(TRACE_PATH, trace_event)

    activity_event = {
        "ts": ts,
        "agent": agent_name,
        "operation": "policy_check",
        "result": "PASS" if verdict == "PASS" else "BLOCK",
        "evidence": {
            "governance_outputs": str(GOV_OUT_PATH),
            "guardian_trace": str(TRACE_PATH),
            "finding_count": len(findings),
            "verdict": verdict
        }
    }
    append_jsonl(ACTIVITY_PATH, activity_event)

    # Hard exit code for governance: BLOCK => non-zero
    return 0 if verdict == "PASS" else 2

if __name__ == "__main__":
    raise SystemExit(main())