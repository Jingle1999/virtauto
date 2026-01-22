#!/usr/bin/env python3
"""virtauto – GEORGE Contract Enforcement (v1)

Purpose
- Make the GEORGE contract *actionable* at runtime (proto-governing).
- Provide a single enforcement primitive that can be called from orchestrators and gates.

Design choices (v1)
- Safe defaults: unknown actions are denied for APPLY (but may be PROPOSED if the mode allows proposing).
- Mode resolution is explicit and auditable:
  1) env var GEORGE_MODE
  2) ops/george_mode.json (if present)
  3) contract.default_mode
- This module does NOT execute actions. It only decides: {propose_ok, apply_ok, reasons}.

NOTE:
- "apply" here means: perform a side-effecting execution step.
- "propose" means: write decision artifacts + traces without execution.
"""

from __future__ import annotations

import fnmatch
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from jsonschema import Draft202012Validator

OPS_DIR = Path(__file__).resolve().parent
CONTRACT_FILE = OPS_DIR / "contracts" / "george_contract_v1.json"
CONTRACT_SCHEMA_FILE = OPS_DIR / "contracts" / "schemas" / "george_contract_v1.schema.json"
MODE_FILE = OPS_DIR / "george_mode.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


@dataclass(frozen=True)
class ContractDecision:
    mode: str
    propose_ok: bool
    apply_ok: bool
    reasons: List[str]
    matched_allowlist_action_id: Optional[str] = None
    matched_deny_pattern: Optional[str] = None


def _validate_contract(contract: Dict[str, Any]) -> Tuple[bool, List[str]]:
    if not CONTRACT_SCHEMA_FILE.exists():
        return True, []
    try:
        schema = load_json(CONTRACT_SCHEMA_FILE, default={})
        v = Draft202012Validator(schema)
        errors = sorted(v.iter_errors(contract), key=lambda e: e.path)
        if errors:
            return False, [f"{list(e.path)}: {e.message}" for e in errors[:25]]
        return True, []
    except Exception as exc:
        return False, [f"contract_schema_validation_failed: {exc}"]


def resolve_mode(contract: Dict[str, Any]) -> str:
    env_mode = os.getenv("GEORGE_MODE", "").strip()
    if env_mode:
        return env_mode

    file_mode = load_json(MODE_FILE, default={})
    if isinstance(file_mode, dict) and file_mode.get("mode"):
        return str(file_mode.get("mode"))

    return str(contract.get("default_mode") or "HUMAN_GUARDED")


def load_contract() -> Dict[str, Any]:
    contract = load_json(CONTRACT_FILE, default={})
    if not isinstance(contract, dict):
        return {}
    ok, errs = _validate_contract(contract)
    if not ok:
        # Keep it strict: an invalid contract is equivalent to "deny apply" everywhere.
        contract.setdefault("_validation", {})
        contract["_validation"] = {"ok": False, "errors": errs, "checked_at": _utc_now()}
    else:
        contract.setdefault("_validation", {})
        contract["_validation"] = {"ok": True, "errors": [], "checked_at": _utc_now()}
    return contract


def _mode_caps(contract: Dict[str, Any], mode: str) -> Dict[str, Any]:
    modes = contract.get("modes") or {}
    if isinstance(modes, dict) and isinstance(modes.get(mode), dict):
        return modes[mode]
    # fallback to default mode config if mode unknown
    default_mode = str(contract.get("default_mode") or "HUMAN_GUARDED")
    if isinstance(modes, dict) and isinstance(modes.get(default_mode), dict):
        return modes[default_mode]
    return {"can_apply": False, "can_propose": True, "requires_human_approval": True}


def _match_allowlist(contract: Dict[str, Any], action_id: str, scope: Optional[str]) -> Optional[Dict[str, Any]]:
    ap = contract.get("action_policy") or {}
    allow = ap.get("allowlist") or []
    if not isinstance(allow, list):
        return None
    for item in allow:
        if not isinstance(item, dict):
            continue
        if str(item.get("action_id")) != action_id:
            continue
        scopes = item.get("scope") or []
        if scope and scopes and scope not in [str(s) for s in scopes]:
            continue
        return item
    return None


def _match_deny(contract: Dict[str, Any], action_id: str) -> Optional[Dict[str, Any]]:
    ap = contract.get("action_policy") or {}
    deny = ap.get("denylist") or []
    if not isinstance(deny, list):
        return None
    for item in deny:
        if not isinstance(item, dict):
            continue
        pattern = str(item.get("pattern") or "")
        if not pattern:
            continue
        if fnmatch.fnmatch(action_id, pattern):
            return item
    return None


def evaluate_action(
    action_id: str,
    *,
    scope: Optional[str] = None,
    contract: Optional[Dict[str, Any]] = None,
    mode: Optional[str] = None,
) -> ContractDecision:
    contract = contract or load_contract()
    mode = mode or resolve_mode(contract)

    caps = _mode_caps(contract, mode)
    can_propose = bool(caps.get("can_propose", True))
    can_apply_mode = bool(caps.get("can_apply", False))

    reasons: List[str] = []

    # Contract invalid => no apply
    validation = contract.get("_validation") or {}
    if validation and not validation.get("ok", True):
        reasons.append("contract_invalid")
        return ContractDecision(mode=mode, propose_ok=can_propose, apply_ok=False, reasons=reasons)

    # Denylist has priority
    deny = _match_deny(contract, action_id)
    if deny:
        reasons.append(f"denylist:{deny.get('pattern')}")
        return ContractDecision(mode=mode, propose_ok=can_propose, apply_ok=False, reasons=reasons, matched_deny_pattern=str(deny.get("pattern")))

    allow_item = _match_allowlist(contract, action_id, scope)
    if not allow_item:
        # Unknown action => deny apply; allow propose if mode allows
        reasons.append("not_in_allowlist")
        return ContractDecision(mode=mode, propose_ok=can_propose, apply_ok=False, reasons=reasons)

    # In allowlist, but mode might still block apply
    if not can_apply_mode:
        reasons.append("mode_disallows_apply")
        return ContractDecision(mode=mode, propose_ok=can_propose, apply_ok=False, reasons=reasons, matched_allowlist_action_id=action_id)

    # If mode requires human approval, treat as propose-only unless overridden elsewhere
    if bool(caps.get("requires_human_approval", False)):
        reasons.append("requires_human_approval")
        return ContractDecision(mode=mode, propose_ok=can_propose, apply_ok=False, reasons=reasons, matched_allowlist_action_id=action_id)

    return ContractDecision(mode=mode, propose_ok=can_propose, apply_ok=True, reasons=reasons, matched_allowlist_action_id=action_id)
