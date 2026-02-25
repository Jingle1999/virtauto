#!/usr/bin/env python3
"""
Governance-Grade Validator (Stage 3 — WARN mode)

Behavior (requested):
- Hard FAIL only on:
  - file missing
  - invalid JSON
  - missing required keys / wrong basic shapes
- Vocabulary / enum mismatches => WARN (not fail)
- ALLOW/PASS without decision_trace => WARN (not fail)
- Unknown top-level keys => WARN (not fail)

Optional strict mode:
- Set VT_STRICT=1 to turn enum mismatches + ALLOW/PASS missing decision_trace into FAIL.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union


STATUS_PATH = Path("ops/reports/system_status.json")
VOCAB_PATH = Path("ops/schemas/system_status_vocab.json")

STRICT = os.getenv("VT_STRICT", "").strip() in ("1", "true", "TRUE", "yes", "YES")


# =========================
# Helpers: output + loading
# =========================
_WARN_COUNT = 0


def die(msg: str) -> None:
    print(f"VALIDATION FAILED: {msg}")
    sys.exit(1)


def warn(msg: str) -> None:
    global _WARN_COUNT
    _WARN_COUNT += 1
    print(f"VALIDATION WARN: {msg}")


def ok(msg: str) -> None:
    print(f"VALIDATION OK: {msg}")


def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        die(f"{path} not found")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        die(f"Invalid JSON in {path}: {e}")


def is_obj(x: Any) -> bool:
    return isinstance(x, dict)


def is_list(x: Any) -> bool:
    return isinstance(x, list)


def upper(v: Any) -> Optional[str]:
    if v is None:
        return None
    s = str(v).strip()
    return s.upper() if s else None


def require_obj(parent: Dict[str, Any], key: str, ctx: str) -> Dict[str, Any]:
    if key not in parent:
        die(f"Missing: {ctx}.{key}")
    if not isinstance(parent[key], dict):
        die(f"{ctx}.{key} must be an object")
    return parent[key]


def require_key(parent: Dict[str, Any], key: str, ctx: str) -> Any:
    if key not in parent:
        die(f"Missing: {ctx}.{key}")
    return parent[key]


# =========================
# Vocab handling
# =========================
def ensure_vocab(vocab: Dict[str, Any]) -> Dict[str, List[str]]:
    required = ["system_state", "agent_state", "autonomy_mode", "health_signal"]
    for k in required:
        if k not in vocab or not isinstance(vocab[k], list) or any(not isinstance(x, str) for x in vocab[k]):
            die(f"Vocab missing/invalid: {k}")
    # normalize to UPPER for comparisons
    return {k: [str(x).strip().upper() for x in vocab[k] if str(x).strip()] for k in required}


def validate_enum(value: Any, allowed: Iterable[str], context: str) -> None:
    v = upper(value)
    if v is None:
        warn(f'{context} is missing/empty (treated as UNKNOWN)')
        return
    allowed_set = set(allowed)
    if v not in allowed_set:
        msg = f'{context} "{v}" not in allowed values: {sorted(allowed_set)}'
        if STRICT:
            die(msg)
        else:
            warn(msg)


# =========================
# Agents normalization
# =========================
AgentMap = Dict[str, Dict[str, Any]]


def agents_as_map(agents_raw: Any) -> AgentMap:
    """
    Accept either:
    - object-map: {"george": {...}, ...}
    - array: [{"agent":"george", ...}, {"key":"guardian", ...}]
    """
    if isinstance(agents_raw, dict):
        out: AgentMap = {}
        for k, v in agents_raw.items():
            if not isinstance(v, dict):
                die(f'agents["{k}"] must be an object')
            out[str(k)] = v
        return out

    if isinstance(agents_raw, list):
        out = {}
        for i, row in enumerate(agents_raw):
            if not isinstance(row, dict):
                die(f"agents[{i}] must be an object")
            key = row.get("agent") or row.get("key") or row.get("name")
            if not key:
                warn(f"agents[{i}] missing agent/key/name; skipping")
                continue
            out[str(key)] = row
        return out

    die("agents must be an object-map or an array")
    raise AssertionError("unreachable")


# =========================
# Main validation
# =========================
def main() -> None:
    data = load_json(STATUS_PATH)
    vocab_raw = load_json(VOCAB_PATH)
    vocab = ensure_vocab(vocab_raw)

    # -------------------------
    # Required top-level keys
    # -------------------------
    require_key(data, "schema_version", "root")
    require_key(data, "generated_at", "root")
    require_key(data, "environment", "root")

    # Accept either:
    # - system_state (top-level) + autonomy (top-level)
    # - plus required "system" object
    require_key(data, "system_state", "root")
    require_key(data, "autonomy", "root")
    system = require_obj(data, "system", "root")

    validate_enum(data.get("system_state"), vocab["system_state"], "system_state")
    validate_enum(system.get("state"), vocab["system_state"], "system.state")
    validate_enum(system.get("autonomy_mode"), vocab["autonomy_mode"], "system.autonomy_mode")
    validate_enum(data.get("autonomy"), vocab["autonomy_mode"], "autonomy")

    # -------------------------
    # Health (optional object)
    # -------------------------
    if "health" in data:
        if not isinstance(data["health"], dict):
            die("health must be an object")
        signal = data["health"].get("signal")
        if signal is not None:
            validate_enum(signal, vocab["health_signal"], "health.signal")

    # -------------------------
    # Agents (required)
    # -------------------------
    agents_raw = require_key(data, "agents", "root")
    agents = agents_as_map(agents_raw)

    for name, agent in agents.items():
        # state optional but if present validate
        if "state" in agent:
            validate_enum(agent.get("state"), vocab["agent_state"], f'agents["{name}"].state')
        else:
            warn(f'agents["{name}"].state missing')

        # autonomy_mode optional but if present validate
        if "autonomy_mode" in agent:
            validate_enum(agent.get("autonomy_mode"), vocab["autonomy_mode"], f'agents["{name}"].autonomy_mode')

    # -------------------------
    # Governance gate rule (WARN-only unless STRICT)
    # ALLOW/PASS requires links.decision_trace
    # -------------------------
    gate_verdict = None
    try:
        gate_verdict = (
            (data.get("autonomy_score") or {})
            .get("inputs", {})
            .get("gate_verdict")
        )
    except Exception:
        gate_verdict = None

    gv = upper(gate_verdict)
    if gv in ("ALLOW", "PASS"):
        links = data.get("links") or {}
        decision_trace = None
        if isinstance(links, dict):
            decision_trace = links.get("decision_trace")
        if not decision_trace:
            msg = "ALLOW/PASS requires audit trail (links.decision_trace missing)"
            if STRICT:
                die(msg)
            else:
                warn(msg)

    # -------------------------
    # Unknown top-level keys => WARN
    # -------------------------
    known_top = {
        "schema_version",
        "generated_at",
        "environment",
        "system_state",
        "autonomy",
        "system",
        "governance",
        "autonomy_model",
        "autonomy_score",
        "health",
        "governance_evidence",
        "agents",
        "links",
    }
    for k in data.keys():
        if k not in known_top:
            warn(f'Unknown top-level key "{k}" (allowed, but review)')

    # -------------------------
    # Summary / exit
    # -------------------------
    if _WARN_COUNT:
        ok(f"system_status.json is valid with {_WARN_COUNT} warning(s). (STRICT={STRICT})")
    else:
        ok(f"system_status.json is governance-grade compliant. (STRICT={STRICT})")
    sys.exit(0)


if __name__ == "__main__":
    main()