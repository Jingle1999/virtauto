#!/usr/bin/env python3
import json
import sys
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

try:
    import yaml  # pip install pyyaml
except ImportError:
    yaml = None


@dataclass
class GateResult:
    verdict: str  # ALLOW | BLOCK | ESCALATE
    reasons: List[str]
    applied_policy: Dict[str, Any]


def _load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_yaml(path: str) -> Dict[str, Any]:
    if yaml is None:
        raise RuntimeError("PyYAML not installed. Add `pyyaml` to requirements.txt.")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _get(d: Dict[str, Any], key_path: str, default=None):
    cur = d
    for part in key_path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return default
        cur = cur[part]
    return cur


def evaluate(decision: Dict[str, Any], policy: Dict[str, Any]) -> GateResult:
    decision_class = decision.get("decision_class")
    if not decision_class:
        return GateResult("BLOCK", ["Missing decision_class"], {"decision_class": None})

    enforcement = policy.get("enforcement", {})
    mode = enforcement.get("mode", "advisory")
    default_action = enforcement.get("default_action", "block").upper()
    allow_override = bool(enforcement.get("allow_human_override", True))

    class_rules = (policy.get("decision_classes") or {}).get(decision_class, {})
    thresholds = policy.get("thresholds", {})
    min_health_default = float(thresholds.get("min_health_score", 0.0))

    # Use per-class threshold if present, else global threshold.
    min_health = float(class_rules.get("min_health_score", min_health_default))

    require_guardian_ok = bool(class_rules.get("require_guardian_ok", False))
    require_trace = bool(class_rules.get("require_trace", False))
    require_status_endpoint = bool(class_rules.get("require_status_endpoint", False))
    on_fail = str(class_rules.get("on_fail", default_action)).upper()

    reasons: List[str] = []

    # Signals (runtime facts)
    health = _get(decision, "signals.system_health_score", None)
    guardian_ok = bool(_get(decision, "signals.guardian_ok", False))
    status_ok = bool(_get(decision, "signals.status_endpoint_ok", False))
    trace_present = bool(_get(decision, "signals.decision_trace_present", False))

    # Validate health
    if health is None:
        reasons.append("Missing signals.system_health_score")
    else:
        try:
            health_f = float(health)
            if health_f < min_health:
                reasons.append(f"Health below threshold: {health_f:.2f} < {min_health:.2f}")
        except Exception:
            reasons.append("Invalid signals.system_health_score (not a number)")

    if require_guardian_ok and not guardian_ok:
        reasons.append("Guardian not OK (require_guardian_ok=true)")

    if require_status_endpoint and not status_ok:
        reasons.append("Status endpoint not OK/unavailable (require_status_endpoint=true)")

    if require_trace and not trace_present:
        reasons.append("Decision trace missing (require_trace=true)")

    # Decide verdict
    if len(reasons) == 0:
        verdict = "ALLOW"
    else:
        # If policy demands ESCALATE but overrides not allowed -> BLOCK
        if on_fail == "ESCALATE" and not allow_override:
            verdict = "BLOCK"
            reasons.append("Human override disabled; ESCALATE downgraded to BLOCK")
        else:
            verdict = on_fail if on_fail in ("BLOCK", "ESCALATE") else default_action

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
    }

    # In advisory mode: never hard BLOCK. Convert BLOCK -> ESCALATE (unless already ALLOW).
    if mode.lower() == "advisory" and verdict == "BLOCK":
        verdict = "ESCALATE"
        reasons.append("Advisory mode: BLOCK converted to ESCALATE")

    return GateResult(verdict, reasons, applied)


def main():
    if len(sys.argv) < 3:
        print("Usage: python ops/runtime_gate.py <decision_json> <policy_yaml> [output_json]")
        sys.exit(2)

    decision_path = sys.argv[1]
    policy_path = sys.argv[2]
    output_path: Optional[str] = sys.argv[3] if len(sys.argv) > 3 else None

    decision = _load_json(decision_path)
    policy = _load_yaml(policy_path)

    result = evaluate(decision, policy)

    out = {
        "decision_id": decision.get("decision_id"),
        "decision_class": decision.get("decision_class"),
        "verdict": result.verdict,
        "reasons": result.reasons,
        "applied_policy": result.applied_policy,
    }

    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2)
    else:
        print(json.dumps(out, indent=2))

    # Exit code enforces blocking in pipelines if desired:
    # 0 = allow, 10 = escalate, 20 = block
    if result.verdict == "ALLOW":
        sys.exit(0)
    if result.verdict == "ESCALATE":
        sys.exit(10)
    sys.exit(20)


if __name__ == "__main__":
    main()
