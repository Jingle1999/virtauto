#!/usr/bin/env python3
"""
ops/consistency_agent.py — Consistency Agent v1 (Website-only)

Purpose:
- Merge-blocking consistency checks for virtauto website truth-chain artifacts.
- Deterministic, no network calls. CI/PR friendly.

Hard fail examples:
- Missing / invalid JSON for required truth artifacts
- Broken cross-links (system_status -> decision_trace, gate_result)
- gate_result.trace_id not found in decision_trace tail window
- decision_trace.jsonl invalid JSON lines in tail window
- Registry missing agents referenced by system_status

Outputs:
- Console summary (PASS/WARN/FAIL)
- Optional machine report: ops/reports/consistency_report.json (generated in working tree)
- Optional GitHub Actions job summary via $GITHUB_STEP_SUMMARY

Exit codes:
- 0 PASS (no FAIL findings)
- 2 FAIL (>=1 FAIL finding)
- 1 TOOL ERROR (unexpected exception)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

try:
    import yaml  # type: ignore
except Exception as e:  # pragma: no cover
    yaml = None


ROOT = Path(".")
DEFAULT_RULES_PATH = Path("ops/consistency_rules.yaml")
DEFAULT_REPORT_PATH = Path("ops/reports/consistency_report.json")


@dataclass(frozen=True)
class Finding:
    level: str  # PASS/WARN/FAIL
    code: str
    msg: str
    path: Optional[str] = None


def iso_utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_iso8601_z(s: str) -> Optional[datetime]:
    # Minimal ISO8601 parser for "...Z" timestamps
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        return datetime.fromisoformat(s)
    except Exception:
        return None


def load_yaml(path: Path) -> Dict[str, Any]:
    if yaml is None:
        raise RuntimeError("PyYAML not available. Install with: pip install pyyaml")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Rules file {path} must parse to a dict/object.")
    return data


def load_json(path: Path) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except Exception:
        return None


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    ensure_parent(path)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def read_jsonl_tail(path: Path, max_lines: int) -> Tuple[List[Dict[str, Any]], List[Finding]]:
    findings: List[Finding] = []
    items: List[Dict[str, Any]] = []

    if not path.exists():
        findings.append(Finding("FAIL", "CNS-TRACE-001", "decision_trace.jsonl missing", str(path)))
        return items, findings

    # Read line-by-line, keep last N only
    dq: deque[str] = deque(maxlen=max_lines)
    try:
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                dq.append(line)
    except Exception as e:
        findings.append(Finding("FAIL", "CNS-TRACE-ERR", f"Failed reading decision_trace.jsonl: {e}", str(path)))
        return items, findings

    if len(dq) == 0:
        findings.append(Finding("FAIL", "CNS-TRACE-002", "decision_trace.jsonl is empty", str(path)))
        return items, findings

    # Parse tail window
    for idx, line in enumerate(dq, start=max(1, 1 + (len(dq) - max_lines))):
        try:
            obj = json.loads(line)
            if isinstance(obj, dict):
                items.append(obj)
            else:
                findings.append(
                    Finding("FAIL", "CNS-TRACE-003", "decision_trace.jsonl line is not a JSON object", str(path))
                )
        except Exception:
            findings.append(
                Finding("FAIL", "CNS-TRACE-004", f"decision_trace.jsonl has invalid JSON in tail window", str(path))
            )
            # keep going to report all parse failures

    return items, findings


def has_required_keys(obj: Dict[str, Any], keys: Iterable[str]) -> List[str]:
    missing: List[str] = []
    for k in keys:
        if k not in obj:
            missing.append(k)
    return missing


def now_utc_dt() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def add_summary_line(lines: List[str], f: Finding) -> None:
    p = f" ({f.path})" if f.path else ""
    lines.append(f"- **{f.level}** `{f.code}`: {f.msg}{p}")


def write_github_summary(findings: List[Finding], status: str) -> None:
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return

    lines: List[str] = []
    lines.append(f"## Consistency Agent v1 — {status}")
    lines.append("")
    if not findings:
        lines.append("- ✅ No findings.")
    else:
        for f in findings:
            add_summary_line(lines, f)

    Path(summary_path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def validate_system_status(
    rules: Dict[str, Any],
    system_status_path: Path,
    decision_trace_path: Path,
    gate_result_path: Path,
    registry: Optional[Dict[str, Any]],
) -> List[Finding]:
    findings: List[Finding] = []

    obj = load_json(system_status_path)
    if obj is None:
        findings.append(Finding("FAIL", "CNS-SSOT-001", "system_status.json missing or invalid JSON", str(system_status_path)))
        return findings

    required_keys = rules["schemas"]["system_status"]["required_keys"]
    missing = has_required_keys(obj, required_keys)
    for k in missing:
        findings.append(Finding("FAIL", "CNS-SSOT-002", f"system_status.json missing key: {k}", str(system_status_path)))

    # link integrity
    links = obj.get("links", {})
    if not isinstance(links, dict):
        findings.append(Finding("FAIL", "CNS-SSOT-003", "system_status.links must be an object", str(system_status_path)))
        links = {}

    exp_trace = str(decision_trace_path).replace("\\", "/")
    exp_gate = str(gate_result_path).replace("\\", "/")

    if links.get("decision_trace") != exp_trace:
        findings.append(
            Finding(
                "FAIL",
                "CNS-SSOT-004",
                f"system_status.links.decision_trace must equal '{exp_trace}'",
                str(system_status_path),
            )
        )
    if links.get("gate_result") != exp_gate:
        findings.append(
            Finding(
                "FAIL",
                "CNS-SSOT-005",
                f"system_status.links.gate_result must equal '{exp_gate}'",
                str(system_status_path),
            )
        )

    # health signal
    health = obj.get("health", {})
    if isinstance(health, dict):
        signal = health.get("signal")
        allowed = rules["values"]["health_signals"]
        if signal not in allowed:
            findings.append(
                Finding(
                    "FAIL",
                    "CNS-HEALTH-001",
                    f"health.signal must be one of {allowed}, got: {signal!r}",
                    str(system_status_path),
                )
            )

    # age warning (soft)
    max_age_min = rules["thresholds"].get("max_generated_age_minutes_warn", None)
    if max_age_min is not None:
        ts = obj.get("generated_at")
        if isinstance(ts, str):
            dt = parse_iso8601_z(ts)
            if dt is None:
                findings.append(Finding("WARN", "CNS-TIME-001", "generated_at not parseable ISO8601", str(system_status_path)))
            else:
                age_min = (now_utc_dt() - dt).total_seconds() / 60.0
                if age_min > float(max_age_min):
                    findings.append(
                        Finding(
                            "WARN",
                            "CNS-TIME-002",
                            f"system_status generated_at is {age_min:.1f} minutes old (warn>{max_age_min})",
                            str(system_status_path),
                        )
                    )

    # registry cross-check: agents in system_status must exist in registry
    agents_obj = obj.get("agents", {})
    if isinstance(agents_obj, dict) and registry is not None:
        reg_agents = registry.get("agents", [])
        reg_ids: set[str] = set()
        if isinstance(reg_agents, list):
            for a in reg_agents:
                if isinstance(a, dict):
                    # support id or name
                    aid = a.get("id") or a.get("name")
                    if isinstance(aid, str):
                        reg_ids.add(aid)

        for agent_id in agents_obj.keys():
            if agent_id not in reg_ids:
                findings.append(
                    Finding(
                        "FAIL",
                        "CNS-REG-002",
                        f"Agent '{agent_id}' present in system_status but missing in agents/registry.yaml",
                        str(system_status_path),
                    )
                )

    return findings


def validate_gate_result(rules: Dict[str, Any], gate_result_path: Path) -> Tuple[Optional[Dict[str, Any]], List[Finding]]:
    findings: List[Finding] = []
    obj = load_json(gate_result_path)
    if obj is None:
        findings.append(Finding("FAIL", "CNS-GATE-001", "gate_result.json missing or invalid JSON", str(gate_result_path)))
        return None, findings

    required_keys = rules["schemas"]["gate_result"]["required_keys"]
    for k in has_required_keys(obj, required_keys):
        findings.append(Finding("FAIL", "CNS-GATE-002", f"gate_result.json missing key: {k}", str(gate_result_path)))

    allowed = rules["values"]["gate_verdicts"]
    verdict = obj.get("gate_verdict")
    if verdict not in allowed:
        findings.append(
            Finding(
                "FAIL",
                "CNS-GATE-003",
                f"gate_verdict must be one of {allowed}, got: {verdict!r}",
                str(gate_result_path),
            )
        )

    return obj, findings


def validate_decision_trace_tail(
    rules: Dict[str, Any], decision_trace_path: Path, gate_trace_id: Optional[str]
) -> List[Finding]:
    findings: List[Finding] = []
    tail_n = int(rules["thresholds"].get("decision_trace_tail_lines", 200))

    items, f2 = read_jsonl_tail(decision_trace_path, tail_n)
    findings.extend(f2)

    if not items:
        # already has findings for missing/empty
        return findings

    required_keys = rules["schemas"]["decision_trace"]["required_keys"]
    seen_trace_ids: set[str] = set()
    dupes: set[str] = set()

    for obj in items:
        for k in has_required_keys(obj, required_keys):
            findings.append(
                Finding("FAIL", "CNS-TRACE-010", f"decision_trace entry missing key: {k}", str(decision_trace_path))
            )

        tid = obj.get("trace_id")
        if isinstance(tid, str):
            if tid in seen_trace_ids:
                dupes.add(tid)
            seen_trace_ids.add(tid)

    if dupes:
        findings.append(
            Finding(
                "FAIL",
                "CNS-TRACE-011",
                f"duplicate trace_id(s) in tail window: {sorted(dupes)[:5]}{'...' if len(dupes) > 5 else ''}",
                str(decision_trace_path),
            )
        )

    if gate_trace_id:
        if gate_trace_id not in seen_trace_ids:
            findings.append(
                Finding(
                    "FAIL",
                    "CNS-TRACE-020",
                    f"gate_result.trace_id '{gate_trace_id}' not found in decision_trace tail window (last {tail_n} lines)",
                    str(decision_trace_path),
                )
            )

    # last entry outputs must include required outputs (best-effort)
    required_outputs = rules["schemas"]["decision_trace"].get("required_outputs_in_latest", [])
    latest = items[-1]
    outs = latest.get("outputs", [])
    if isinstance(outs, list):
        outs_norm = {str(x) for x in outs}
        for req in required_outputs:
            if req not in outs_norm:
                findings.append(
                    Finding(
                        "FAIL",
                        "CNS-TRACE-030",
                        f"latest decision_trace.outputs must include '{req}'",
                        str(decision_trace_path),
                    )
                )

    return findings


def validate_registry(rules: Dict[str, Any], registry_path: Path) -> Tuple[Optional[Dict[str, Any]], List[Finding]]:
    findings: List[Finding] = []
    if not registry_path.exists():
        findings.append(Finding("FAIL", "CNS-REG-001", "agents/registry.yaml missing", str(registry_path)))
        return None, findings

    if yaml is None:
        findings.append(Finding("FAIL", "CNS-REG-ERR", "PyYAML missing (cannot parse registry.yaml)", str(registry_path)))
        return None, findings

    try:
        reg = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
        if not isinstance(reg, dict):
            findings.append(Finding("FAIL", "CNS-REG-003", "registry.yaml must be a YAML mapping/object", str(registry_path)))
            return None, findings
    except Exception as e:
        findings.append(Finding("FAIL", "CNS-REG-004", f"registry.yaml parse error: {e}", str(registry_path)))
        return None, findings

    agents = reg.get("agents")
    if not isinstance(agents, list) or len(agents) == 0:
        findings.append(Finding("FAIL", "CNS-REG-005", "registry.yaml must contain non-empty 'agents' list", str(registry_path)))
        return reg, findings

    required_fields = rules["schemas"]["registry"]["required_agent_fields"]
    allowed_modes = set(rules["values"]["autonomy_modes"])
    allowed_states = set(rules["values"]["agent_states"])

    for a in agents:
        if not isinstance(a, dict):
            findings.append(Finding("FAIL", "CNS-REG-006", "Each agents[] entry must be an object", str(registry_path)))
            continue

        for f in required_fields:
            if f not in a:
                findings.append(Finding("FAIL", "CNS-REG-007", f"Agent missing field: {f}", str(registry_path)))

        mode = a.get("autonomy_mode")
        if mode is not None and mode not in allowed_modes:
            findings.append(
                Finding("FAIL", "CNS-REG-008", f"Invalid autonomy_mode: {mode!r} (allowed: {sorted(allowed_modes)})", str(registry_path))
            )

        state = a.get("state")
        if state is not None and state not in allowed_states:
            findings.append(
                Finding("FAIL", "CNS-REG-009", f"Invalid state: {state!r} (allowed: {sorted(allowed_states)})", str(registry_path))
            )

    return reg, findings


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rules", default=str(DEFAULT_RULES_PATH), help="path to ops/consistency_rules.yaml")
    ap.add_argument("--report", default=str(DEFAULT_REPORT_PATH), help="path for machine-readable report json")
    ap.add_argument("--mode", default="local", choices=["local", "ci"], help="write GitHub summary in ci mode")
    args = ap.parse_args()

    ts = iso_utc_now()
    findings: List[Finding] = []

    try:
        rules_path = Path(args.rules)
        rules = load_yaml(rules_path) if rules_path.exists() else load_yaml(DEFAULT_RULES_PATH)

        # Resolve paths from rules
        paths = rules["paths"]
        system_status_path = Path(paths["system_status"])
        decision_trace_path = Path(paths["decision_trace_jsonl"])
        gate_result_path = Path(paths["gate_result"])
        registry_path = Path(paths["registry"])

        # required files presence (quick)
        for p in rules.get("required_files", []):
            if not Path(p).exists():
                findings.append(Finding("FAIL", "CNS-REQ-001", f"Required file missing: {p}", p))

        # registry first (for cross-check)
        registry, f_reg = validate_registry(rules, registry_path)
        findings.extend(f_reg)

        # gate_result
        gate_obj, f_gate = validate_gate_result(rules, gate_result_path)
        findings.extend(f_gate)
        gate_trace_id = None
        if gate_obj and isinstance(gate_obj.get("trace_id"), str):
            gate_trace_id = str(gate_obj["trace_id"])

        # decision_trace tail checks
        findings.extend(validate_decision_trace_tail(rules, decision_trace_path, gate_trace_id))

        # system_status checks
        findings.extend(
            validate_system_status(
                rules,
                system_status_path=system_status_path,
                decision_trace_path=decision_trace_path,
                gate_result_path=gate_result_path,
                registry=registry,
            )
        )

        # Compute status
        has_fail = any(f.level == "FAIL" for f in findings)
        has_warn = any(f.level == "WARN" for f in findings)
        status = "FAIL" if has_fail else ("WARN" if has_warn else "PASS")

        # machine report
        report_obj = {
            "status": status,
            "generated_at": ts,
            "agent": "consistency_agent_v1",
            "findings": [
                {"level": f.level, "code": f.code, "msg": f.msg, "path": f.path} for f in findings
            ],
        }
        write_json(Path(args.report), report_obj)

        # console output
        print(f"[Consistency Agent v1] {status}")
        for f in findings:
            p = f" ({f.path})" if f.path else ""
            print(f"- {f.level} {f.code}: {f.msg}{p}")

        # GitHub summary
        if args.mode == "ci":
            write_github_summary(findings, status)

        return 2 if has_fail else 0

    except Exception as e:
        # tool error -> fail closed
        err = Finding("FAIL", "CNS-TOOL-ERR", f"Consistency Agent crashed: {e}")
        findings.append(err)
        try:
            write_json(
                Path(args.report),
                {
                    "status": "FAIL",
                    "generated_at": ts,
                    "agent": "consistency_agent_v1",
                    "findings": [{"level": err.level, "code": err.code, "msg": err.msg, "path": err.path}],
                },
            )
        except Exception:
            pass
        print(f"[Consistency Agent v1] FAIL (tool error): {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
