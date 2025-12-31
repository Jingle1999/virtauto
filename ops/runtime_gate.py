#!/usr/bin/env python3
"""
Runtime Authority Gate (ops/runtime_gate.py)

Goal:
- Evaluate a decision JSON against a runtime gate policy YAML.
- Emit a deterministic gate_result JSON (ALWAYS written if output path is provided).
- Exit codes:
    0  = ALLOW
    10 = ESCALATE   (pipeline should stop + produce review artifacts + ToDo)
    20 = BLOCK
"""

import json
import sys
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

try:
    import yaml  # pip install pyyaml
except ImportError:
    yaml = None


@dataclass
class GateResult:
    verdict: str  # ALLOW | BLOCK | ESCALATE
    reasons: List[str]
    applied_policy: Dict[str, Any]
    exit_code: int
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
        return yaml.safe_load(f)


def _get(d: Any, key_path: str, default=None):
    """Safe nested-get for dicts using dotted paths."""
    cur = d
    for part in key_path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return default
        cur = cur[part]
    return cur


def _as_float(v: Any) -> Optional[float]:
    try:
        if v is None:
            return None
        return float(v)
    except Exception:
        return None


def _as_bool(v: Any) -> Optional[bool]:
    if v is None:
        return None
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return bool(v)
    if isinstance(v, str):
        s = v.strip().lower()
        if s in ("true", "1", "yes", "y", "ok"):
            return True
        if s in ("false", "0", "no", "n"):
            return False
    return None


# -----------------------------
# Signal extraction (robust)
# -----------------------------
def _extract_health_score(decision: Dict[str, Any]) -> Tuple[Optional[float], Optional[str]]:
    """
    Try multiple sources to avoid "structure mismatch" causing false gate blocks.

    Preferred:
      - signals.system_health_score
    Fallbacks:
      - health_context.system_health_score
      - health_context.system_health_percent (0-100 -> /100)
      - health_context.system_health (if numeric)
      - health_context.health_score (legacy)
    """
    candidates = [
        ("signals.system_health_score", _get(decision, "signals.system_health_score")),
        ("health_context.system_health_score", _get(decision, "health_context.system_health_score")),
        ("health_context.system_health_percent", _get(decision, "health_context.system_health_percent")),
        ("health_context.system_health", _get(decision, "health_context.system_health")),
        ("health_context.health_score", _get(decision, "health_context.health_score")),
    ]

    for path, raw in candidates:
        if raw is None:
            continue
        f = _as_float(raw)
        if f is None:
            continue
        # percent -> score
        if path.endswith("system_health_percent") and f > 1.0:
            return max(0.0, min(1.0, f / 100.0)), path
        return max(0.0, min(1.0, f)), path

    return None, None


def _extract_guardian_ok(decision: Dict[str, Any]) -> Tuple[Optional[bool], Optional[str]]:
    """
    Preferred:
      - signals.guardian_ok
    Fallbacks:
      - guardian.ok
      - guardian.status == "OK"
      - guardian_status (top-level legacy) == "OK"
    """
    candidates = [
        ("signals.guardian_ok", _get(decision, "signals.guardian_ok")),
        ("guardian.ok", _get(decision, "guardian.ok")),
        ("guardian.status", _get(decision, "guardian.status")),
        ("guardian_status", decision.get("guardian_status")),
        ("health_context.guardian_ok", _get(decision, "health_context.guardian_ok")),
        ("health_context.guardian_status", _get(decision, "health_context.guardian_status")),
    ]

    for path, raw in candidates:
        if raw is None:
            continue
        if path.endswith(".status") or path.endswith("_status"):
            if isinstance(raw, str):
                s = raw.strip().upper()
                if s == "OK":
                    return True, path
                if s in ("WARNING", "FAIL", "FAILED", "ERROR"):
                    return False, path
        b = _as_bool(raw)
        if b is not None:
            return b, path

    return None, None


def _extract_status_endpoint_ok(decision: Dict[str, Any]) -> Tuple[Optional[bool], Optional[str]]:
    """
    Preferred:
      - signals.status_endpoint_ok
    Fallbacks:
      - health_context.status_endpoint_ok
      - signals.status_endpoint (bool legacy)
    """
    candidates = [
        ("signals.status_endpoint_ok", _get(decision, "signals.status_endpoint_ok")),
        ("health_context.status_endpoint_ok", _get(decision, "health_context.status_endpoint_ok")),
        ("signals.status_endpoint", _get(decision, "signals.status_endpoint")),
    ]
    for path, raw in candidates:
        if raw is None:
            continue
        b = _as_bool(raw)
        if b is not None:
            return b, path
    return None, None


def _extract_trace_present(decision: Dict[str, Any]) -> Tuple[Optional[bool], Optional[str]]:
    """
    Preferred:
      - signals.decision_trace_present
    Fallbacks:
      - decision_trace_present (top-level)
      - decision_trace.trace_id exists
      - decision_trace (dict) non-empty
      - trace (dict) non-empty
    """
    candidates = [
        ("signals.decision_trace_present", _get(decision, "signals.decision_trace_present")),
        ("decision_trace_present", decision.get("decision_trace_present")),
        ("decision_trace.trace_id", _get(decision, "decision_trace.trace_id")),
        ("decision_trace", decision.get("decision_trace")),
        ("trace", decision.get("trace")),
    ]

    for path, raw in candidates:
        if raw is None:
            continue
        if path.endswith("trace_id"):
            # Any non-empty trace_id counts as present
            if isinstance(raw, str) and raw.strip():
                return True, path
        if isinstance(raw, dict):
            return (True if len(raw.keys()) > 0 else False), path
        b = _as_bool(raw)
        if b is not None:
            return b, path

    return None, None


# -----------------------------
# Core evaluation
# -----------------------------
def evaluate(decision: Dict[str, Any], policy: Dict[str, Any]) -> GateResult:
    # Identify decision class (accept some aliases to prevent "structure mismatch" blocks)
    decision_class = decision.get("decision_class") or decision.get("decisionClass") or decision.get("class")
    if not decision_class:
        reasons = ["Missing decision_class (expected decision.decision_class)"]
        applied = {"decision_class": None}
        return GateResult("BLOCK", reasons, applied, 20, ["Fix decision JSON: add decision_class"])

    enforcement = policy.get("enforcement", {}) or {}
    mode = str(enforcement.get("mode", "advisory")).lower()  # advisory | enforced
    default_action = str(enforcement.get("default_action", "block")).upper()
    allow_override = bool(enforcement.get("allow_human_override", True))

    class_rules = (policy.get("decision_classes") or {}).get(decision_class, {}) or {}
    thresholds = policy.get("thresholds", {}) or {}
    min_health_default = float(thresholds.get("min_health_score", 0.0))

    # Use per-class threshold if present, else global threshold.
    min_health = float(class_rules.get("min_health_score", min_health_default))

    require_guardian_ok = bool(class_rules.get("require_guardian_ok", False))
    require_trace = bool(class_rules.get("require_trace", False))
    require_status_endpoint = bool(class_rules.get("require_status_endpoint", False))
    on_fail = str(class_rules.get("on_fail", default_action)).upper()

    reasons: List[str] = []
    todo: List[str] = []

    # Extract signals robustly
    health, health_src = _extract_health_score(decision)
    guardian_ok, guardian_src = _extract_guardian_ok(decision)
    status_ok, status_src = _extract_status_endpoint_ok(decision)
    trace_present, trace_src = _extract_trace_present(decision)

    # Health validation
    if health is None:
        reasons.append("Missing system health score (signals.system_health_score or health_context.*)")
        todo.append("Ensure decision includes a reproducible health score (0..1) in signals.system_health_score.")
    else:
        if health < min_health:
            reasons.append(f"Health below threshold: {health:.2f} < {min_health:.2f}")
            todo.append("Investigate why health is below threshold; fix baseline/cold-start health signals.")

    # Guardian validation
    if require_guardian_ok:
        if guardian_ok is None:
            reasons.append("Guardian OK required but missing (signals.guardian_ok / guardian.*)")
            todo.append("Ensure guardian emits ok/status into decision (signals.guardian_ok or guardian.ok).")
        elif guardian_ok is False:
            reasons.append("Guardian not OK (require_guardian_ok=true)")
            todo.append("Resolve guardian warning/failure or allow explicit human override workflow.")

    # Status endpoint validation
    if require_status_endpoint:
        if status_ok is None:
            reasons.append("Status endpoint required but missing (signals.status_endpoint_ok / health_context.*)")
            todo.append("Populate signals.status_endpoint_ok (true/false) deterministically.")
        elif status_ok is False:
            reasons.append("Status endpoint not OK/unavailable (require_status_endpoint=true)")
            todo.append("Fix status endpoint check or temporarily relax require_status_endpoint for this class.")

    # Trace validation
    if require_trace:
        if trace_present is None:
            reasons.append("Decision trace required but missing (signals.decision_trace_present / decision_trace.*)")
            todo.append("Write decision_trace.jsonl per decision and mark presence in decision signals.")
        elif trace_present is False:
            reasons.append("Decision trace missing/empty (require_trace=true)")
            todo.append("Ensure decision_trace.jsonl contains deterministic required fields for this decision.")

    # Decide verdict
    if not reasons:
        verdict = "ALLOW"
    else:
        # Normalize on_fail
        if on_fail not in ("BLOCK", "ESCALATE"):
            on_fail = default_action if default_action in ("BLOCK", "ESCALATE") else "BLOCK"

        # If policy demands ESCALATE but overrides not allowed -> BLOCK
        if on_fail == "ESCALATE" and not allow_override:
            verdict = "BLOCK"
            reasons.append("Human override disabled; ESCALATE downgraded to BLOCK")
            todo.append("Either enable allow_human_override or set on_fail=BLOCK for this decision class.")
        else:
            verdict = on_fail

    # Advisory mode: never hard BLOCK (convert BLOCK -> ESCALATE)
    if mode == "advisory" and verdict == "BLOCK":
        verdict = "ESCALATE"
        reasons.append("Advisory mode: BLOCK converted to ESCALATE")
        todo.append("Advisory mode: review required; no hard block will be enforced.")

    # Determine exit code (pipeline behavior)
    if verdict == "ALLOW":
        exit_code = 0
    elif verdict == "ESCALATE":
        exit_code = 10
    else:
        exit_code = 20

    applied = {
        "mode": mode,
        "decision_class": decision_class,
        "min_health_score": min_health,
        "require_guardian_ok": require_guardian_ok,
        "require_status_endpoint": require_status_endpoint,
        "require_trace": require_trace,
        "on_fail": on_fail,
        "default_action": default_action,
        "allow_human_override": allow_override,
        "signal_sources": {
            "system_health_score": health_src,
            "guardian_ok": guardian_src,
            "status_endpoint_ok": status_src,
            "decision_trace_present": trace_src,
        },
    }

    # For ESCALATE we explicitly include a “review artifact expectation”
    if verdict == "ESCALATE":
        todo.append("ESCALATE: stop pipeline, upload gate_result.json + decision JSON + trace artifact, open ToDo/Review.")

    return GateResult(verdict, reasons, applied, exit_code, todo)


def _write_output(path: str, payload: Dict[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def main():
    if len(sys.argv) < 3:
        print("Usage: python ops/runtime_gate.py <decision_json> <policy_yaml> [output_json]")
        sys.exit(2)

    decision_path = sys.argv[1]
    policy_path = sys.argv[2]
    output_path: Optional[str] = sys.argv[3] if len(sys.argv) > 3 else None

    out: Dict[str, Any] = {}
    exit_code = 20

    try:
        decision = _load_json(decision_path)
        policy = _load_yaml(policy_path)

        result = evaluate(decision, policy)

        out = {
            "schema_version": "1.0",
            "decision_id": decision.get("decision_id") or decision.get("id"),
            "decision_class": decision.get("decision_class") or decision.get("decisionClass") or decision.get("class"),
            "verdict": result.verdict,
            "exit_code": result.exit_code,
            "reasons": result.reasons,
            "todo": result.todo,
            "applied_policy": result.applied_policy,
        }
        exit_code = result.exit_code

    except Exception as e:
        # IMPORTANT: never fail silently; persist a structured gate result if possible.
        out = {
            "schema_version": "1.0",
            "decision_id": None,
            "decision_class": None,
            "verdict": "BLOCK",
            "exit_code": 20,
            "reasons": [f"runtime_gate exception: {type(e).__name__}: {e}"],
            "todo": ["Fix runtime_gate crash; ensure decision/policy are readable and valid."],
            "applied_policy": {"mode": None},
        }
        exit_code = 20

    if output_path:
        try:
            _write_output(output_path, out)
        except Exception as e:
            # If writing fails, at least print.
            print(json.dumps(out, indent=2, ensure_ascii=False))
            print(f"[runtime_gate] WARNING: failed to write output_json: {type(e).__name__}: {e}", file=sys.stderr)
    else:
        print(json.dumps(out, indent=2, ensure_ascii=False))

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
