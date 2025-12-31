#!/usr/bin/env python3
"""
runtime_gate.py — Runtime authority gate for GEORGE

Design goals (Build-Phase):
- Never fail due to *structure* surprises: tolerate missing/moved keys and still emit a gate_result.json.
- ESCALATE/BLOCK semantics are expressed in the output (verdict + exit_code), but this script
  should NOT necessarily stop the workflow by itself. The workflow can stop later (authoritative step)
  while still uploading review artifacts.

Exit behavior:
- By default, this script exits 0 in all cases (so downstream artifact steps still run).
- If you want the legacy “hard stop here” behavior, pass `--hard-exit` to use exit codes:
  0=ALLOW, 10=ESCALATE, 20=BLOCK
"""

import json
import sys
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

try:
    import yaml  # pip install pyyaml
except ImportError:
    yaml = None


# -----------------------------
# Data model
# -----------------------------
@dataclass
class GateResult:
    verdict: str  # ALLOW | ESCALATE | BLOCK
    reasons: List[str]
    applied_policy: Dict[str, Any]
    exit_code: int  # 0 | 10 | 20
    todo: List[str]


# -----------------------------
# IO helpers
# -----------------------------
def _load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_yaml(path: str) -> Dict[str, Any]:
    if yaml is None:
        raise RuntimeError("PyYAML not installed. Add `pyyaml` to requirements.txt.")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _atomic_write_json(path: str, payload: Dict[str, Any]) -> None:
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
        f.write("\n")
    # atomic-ish rename on POSIX
    try:
        import os

        os.replace(tmp, path)
    except Exception:
        # fallback
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
            f.write("\n")


def _get(d: Any, key_path: str, default=None):
    cur = d
    for part in key_path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return default
        cur = cur[part]
    return cur


# -----------------------------
# Signal normalization
# -----------------------------
def _first_present(decision: Dict[str, Any], paths: List[str], default=None):
    for p in paths:
        v = _get(decision, p, None)
        if v is not None:
            return v
    return default


def _coerce_float(v: Any) -> Optional[float]:
    if v is None:
        return None
    try:
        return float(v)
    except Exception:
        return None


def _normalize_signals(decision: Dict[str, Any]) -> Dict[str, Any]:
    """
    Accept multiple schema variants and normalize into a single signal dict.
    Supported locations:
      - decision.signals.*
      - decision.execution_context.signals.*
      - decision.health_context.* (fallback/derivation)
      - decision.guardian.* or decision.guardian_status/guardian_flag (fallback)
    """
    signals: Dict[str, Any] = {}

    # Prefer explicit signals
    raw_signals = _first_present(
        decision,
        ["signals", "execution_context.signals"],
        default={},
    )
    if isinstance(raw_signals, dict):
        signals.update(raw_signals)

    # Health score: prefer explicit; else derive from health_context
    health = signals.get("system_health_score")
    if health is None:
        # common alternates
        health = _first_present(
            decision,
            [
                "health_context.system_health_score",
                "health_context.system_health",  # some schemas use 0..1
                "health_context.health_score",
                "system_status.health_score",
            ],
            default=None,
        )
    health_f = _coerce_float(health)
    if health_f is not None:
        # If somebody passes percent (0..100), normalize to 0..1
        if health_f > 1.0 and health_f <= 100.0:
            health_f = health_f / 100.0
        # clamp
        health_f = max(0.0, min(1.0, health_f))
        signals["system_health_score"] = health_f

    # Status endpoint ok (best-effort)
    if "status_endpoint_ok" not in signals:
        status_ok = _first_present(
            decision,
            ["signals.status_endpoint_ok", "execution_context.signals.status_endpoint_ok"],
            default=None,
        )
        if status_ok is None:
            # if you store a status endpoint string, treat as "known" but not "ok"
            status_ok = False
        signals["status_endpoint_ok"] = bool(status_ok)

    # Decision trace present: explicit or infer by presence of decision_trace / trace fields
    if "decision_trace_present" not in signals:
        trace_present = _first_present(
            decision,
            ["signals.decision_trace_present", "execution_context.signals.decision_trace_present"],
            default=None,
        )
        if trace_present is None:
            # infer if a trace object exists
            trace_present = _first_present(
                decision,
                ["decision_trace", "trace", "decision_traceability"],
                default=None,
            )
            trace_present = bool(trace_present)
        signals["decision_trace_present"] = bool(trace_present)

    # Guardian ok: explicit, else infer from guardian/guardian_status
    if "guardian_ok" not in signals:
        guardian_ok = _first_present(
            decision,
            ["signals.guardian_ok", "execution_context.signals.guardian_ok"],
            default=None,
        )
        if guardian_ok is None:
            g_ok = _first_present(decision, ["guardian.ok"], default=None)
            if g_ok is not None:
                guardian_ok = bool(g_ok)
            else:
                g_status = _first_present(decision, ["guardian.status", "health_context.guardian_status"], default=None)
                # treat OK (case-insensitive) as ok; anything else not ok
                if isinstance(g_status, str):
                    guardian_ok = (g_status.strip().upper() == "OK")
                else:
                    guardian_ok = False
        signals["guardian_ok"] = bool(guardian_ok)

    return signals


# -----------------------------
# Policy evaluation
# -----------------------------
def _mk_todo(reasons: List[str], decision_class: Optional[str]) -> List[str]:
    todo: List[str] = []
    for r in reasons:
        r_low = r.lower()
        if "missing decision_class" in r_low:
            todo.append("Fix latest.json: add a valid `decision_class` matching the policy (e.g., operational/deploy/etc.).")
        if "missing signals.system_health_score" in r_low or "invalid signals.system_health_score" in r_low:
            todo.append("Fix signals: ensure `system_health_score` is written (0..1) deterministically on every decision.")
        if "health below threshold" in r_low:
            todo.append("Investigate health regression: set correct baseline (avoid cold-start 0.0) or adjust thresholds intentionally.")
        if "guardian not ok" in r_low:
            todo.append("Fix Guardian signal: ensure Guardian runs and writes `guardian_ok=true` when healthy, or adjust require_guardian_ok for class.")
        if "status endpoint not ok" in r_low:
            todo.append("Fix status endpoint check or set `require_status_endpoint=false` for this decision_class if not applicable.")
        if "decision trace missing" in r_low:
            todo.append("Ensure decision_trace.jsonl is written before gating and `decision_trace_present=true` is set.")
    # de-dupe while preserving order
    seen = set()
    deduped: List[str] = []
    for t in todo:
        if t not in seen:
            deduped.append(t)
            seen.add(t)
    if not deduped and reasons:
        # generic fallback
        dc = decision_class or "unknown"
        deduped.append(f"Review gate reasons for decision_class='{dc}' and apply the required fixes.")
    return deduped


def evaluate(decision: Dict[str, Any], policy: Dict[str, Any]) -> GateResult:
    # Decision class (tolerant)
    decision_class = decision.get("decision_class") or decision.get("decisionClass")
    if not decision_class:
        decision_class = None  # keep None for reporting

    enforcement = policy.get("enforcement", {}) or {}
    mode = str(enforcement.get("mode", "advisory")).lower()
    default_action = str(enforcement.get("default_action", "block")).upper()
    allow_override = bool(enforcement.get("allow_human_override", True))

    thresholds = policy.get("thresholds", {}) or {}
    min_health_default = _coerce_float(thresholds.get("min_health_score"))
    if min_health_default is None:
        min_health_default = 0.0

    # Per-class rules
    class_rules: Dict[str, Any] = {}
    if decision_class and isinstance(policy.get("decision_classes"), dict):
        class_rules = (policy.get("decision_classes") or {}).get(decision_class, {}) or {}

    # Use per-class threshold if present, else global
    min_health = _coerce_float(class_rules.get("min_health_score"))
    if min_health is None:
        min_health = float(min_health_default)

    require_guardian_ok = bool(class_rules.get("require_guardian_ok", False))
    require_trace = bool(class_rules.get("require_trace", False))
    require_status_endpoint = bool(class_rules.get("require_status_endpoint", False))
    on_fail = str(class_rules.get("on_fail", default_action)).upper()

    reasons: List[str] = []

    if decision_class is None:
        reasons.append("Missing decision_class")

    signals = _normalize_signals(decision)

    health = signals.get("system_health_score", None)
    guardian_ok = bool(signals.get("guardian_ok", False))
    status_ok = bool(signals.get("status_endpoint_ok", False))
    trace_present = bool(signals.get("decision_trace_present", False))

    # Validate health
    if health is None:
        reasons.append("Missing signals.system_health_score")
    else:
        health_f = _coerce_float(health)
        if health_f is None:
            reasons.append("Invalid signals.system_health_score (not a number)")
        else:
            if health_f < float(min_health):
                reasons.append(f"Health below threshold: {health_f:.2f} < {float(min_health):.2f}")

    if require_guardian_ok and not guardian_ok:
        reasons.append("Guardian not OK (require_guardian_ok=true)")

    if require_status_endpoint and not status_ok:
        reasons.append("Status endpoint not OK/unavailable (require_status_endpoint=true)")

    if require_trace and not trace_present:
        reasons.append("Decision trace missing (require_trace=true)")

    # Determine verdict
    if not reasons:
        verdict = "ALLOW"
    else:
        if on_fail not in ("BLOCK", "ESCALATE"):
            verdict = default_action if default_action in ("BLOCK", "ESCALATE") else "BLOCK"
        else:
            verdict = on_fail

        # If policy demands ESCALATE but overrides not allowed -> BLOCK
        if verdict == "ESCALATE" and not allow_override:
            verdict = "BLOCK"
            reasons.append("Human override disabled; ESCALATE downgraded to BLOCK")

    # In advisory mode: never hard BLOCK. Convert BLOCK -> ESCALATE (unless already ALLOW).
    if mode == "advisory" and verdict == "BLOCK":
        verdict = "ESCALATE"
        reasons.append("Advisory mode: BLOCK converted to ESCALATE")

    exit_code = 0 if verdict == "ALLOW" else (10 if verdict == "ESCALATE" else 20)

    applied = {
        "mode": mode,
        "decision_class": decision_class,
        "min_health_score": float(min_health),
        "require_guardian_ok": require_guardian_ok,
        "require_status_endpoint": require_status_endpoint,
        "require_trace": require_trace,
        "on_fail": on_fail,
        "default_action": default_action,
        "allow_human_override": allow_override,
        # helpful: echo what we actually evaluated
        "signals_used": {
            "system_health_score": signals.get("system_health_score", None),
            "guardian_ok": guardian_ok,
            "status_endpoint_ok": status_ok,
            "decision_trace_present": trace_present,
        },
    }

    todo = _mk_todo(reasons, decision_class)

    return GateResult(verdict=verdict, reasons=reasons, applied_policy=applied, exit_code=exit_code, todo=todo)


# -----------------------------
# CLI
# -----------------------------
def _parse_args(argv: List[str]) -> Tuple[Optional[str], Optional[str], Optional[str], bool]:
    """
    Usage:
      python ops/runtime_gate.py <decision_json> <policy_yaml> [output_json] [--hard-exit]
    """
    hard_exit = False
    args = [a for a in argv[1:] if a.strip()]

    if "--hard-exit" in args:
        hard_exit = True
        args = [a for a in args if a != "--hard-exit"]

    decision_path = args[0] if len(args) >= 1 else None
    policy_path = args[1] if len(args) >= 2 else None
    output_path = args[2] if len(args) >= 3 else None
    return decision_path, policy_path, output_path, hard_exit


def main() -> None:
    decision_path, policy_path, output_path, hard_exit = _parse_args(sys.argv)

    if not decision_path or not policy_path:
        msg = "Usage: python ops/runtime_gate.py <decision_json> <policy_yaml> [output_json] [--hard-exit]"
        print(msg)
        # Even on usage errors, try to write an output if provided (rare)
        if output_path:
            out = {
                "decision_id": None,
                "decision_class": None,
                "verdict": "ESCALATE",
                "exit_code": 10,
                "reasons": [msg],
                "applied_policy": {},
                "todo": ["Fix invocation arguments for runtime_gate.py."],
            }
            _atomic_write_json(output_path, out)
        sys.exit(2)

    # Always emit a gate_result, even if something breaks.
    decision: Dict[str, Any] = {}
    policy: Dict[str, Any] = {}
    fatal_reasons: List[str] = []

    try:
        decision = _load_json(decision_path)
    except Exception as e:
        fatal_reasons.append(f"Decision JSON unreadable: {e!r}")

    try:
        policy = _load_yaml(policy_path)
    except Exception as e:
        fatal_reasons.append(f"Policy YAML unreadable: {e!r}")

    if fatal_reasons:
        # Structural errors should not explode the pipeline: emit ESCALATE with actionable todo.
        result = GateResult(
            verdict="ESCALATE",
            reasons=fatal_reasons,
            applied_policy={"mode": "enforced", "note": "Failed to load inputs; cannot evaluate policy deterministically."},
            exit_code=10,
            todo=[
                "Ensure decision_json and policy_yaml exist and are readable in the workflow workspace.",
                "Add a debug step to `ls -la` the referenced paths and `cat` the files (or upload as artifacts).",
            ],
        )
        out = {
            "decision_id": decision.get("decision_id") if isinstance(decision, dict) else None,
            "decision_class": decision.get("decision_class") if isinstance(decision, dict) else None,
            "verdict": result.verdict,
            "exit_code": result.exit_code,
            "reasons": result.reasons,
            "applied_policy": result.applied_policy,
            "todo": result.todo,
        }
        if output_path:
            _atomic_write_json(output_path, out)
        else:
            print(json.dumps(out, indent=2, ensure_ascii=False))
        sys.exit(result.exit_code if hard_exit else 0)

    # Normal evaluation
    result = evaluate(decision, policy)

    out = {
        "decision_id": decision.get("decision_id") or decision.get("id"),
        "decision_class": decision.get("decision_class"),
        "verdict": result.verdict,
        "exit_code": result.exit_code,
        "reasons": result.reasons,
        "applied_policy": result.applied_policy,
        "todo": result.todo,
    }

    if output_path:
        _atomic_write_json(output_path, out)
    else:
        print(json.dumps(out, indent=2, ensure_ascii=False))

    # Default: do NOT stop the pipeline here (so review artifacts can still be produced).
    # The workflow can enforce stop later based on gate_result.json.
    sys.exit(result.exit_code if hard_exit else 0)


if __name__ == "__main__":
    main()
