from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List


LATEST_TEMPLATE = Path("self_healing/templates/latest.template.json")
STATUS_TEMPLATE = Path("self_healing/templates/system_status.template.json")


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    ensure_parent(path)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl_append(path: Path, record: Dict[str, Any]) -> None:
    ensure_parent(path)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, sort_keys=True) + "\n")


def load_template(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def apply(missing: List[str], trigger: str) -> Dict[str, Any]:
    """
    Create minimal valid placeholders for missing mandatory artifacts.
    This is PR-only: it modifies the working tree, caller will commit on a branch.
    """
    changed: List[str] = []
    now = utc_now()

    # decision_trace.jsonl (mandatory)
    trace_path = Path("ops/reports/decision_trace.jsonl")
    if str(trace_path) in missing:
        write_jsonl_append(trace_path, {
            "decision_type": "SELF_HEALING_PLACEHOLDER",
            "regression_id": "R3",
            "detector": "detect_artifact_regression",
            "playbook": "restore_missing_artifacts",
            "action": "CREATE_PLACEHOLDER",
            "authority": "SYSTEM",
            "result": "ESCALATED_TO_HUMAN",
            "timestamp": now,
            "note": "Placeholder created because mandatory artifact was missing."
        })
        changed.append(str(trace_path))

    # gate_result.json (mandatory)
    gate_path = Path("ops/decisions/gate_result.json")
    if str(gate_path) in missing:
        write_json(gate_path, {
            "schema_version": "1.0",
            "generated_at": now,
            "verdict": "UNKNOWN",
            "reason": "Placeholder created by Self-Healing (R3)",
            "authority": "SYSTEM",
            "details": {
                "trigger": trigger
            }
        })
        changed.append(str(gate_path))

    # system_status.json (mandatory)
    status_path = Path("ops/reports/system_status.json")
    if str(status_path) in missing:
        tpl = load_template(STATUS_TEMPLATE)
        tpl["generated_at"] = now
        tpl["environment"] = tpl.get("environment") or "production"
        tpl["system"]["state"] = "UNKNOWN"
        tpl["health"]["signal"] = "UNKNOWN"
        tpl["health"]["overall_score"] = 0
        tpl.setdefault("links", {})
        tpl["links"]["self_healing_note"] = "Placeholder created by Self-Healing (R3)"
        write_json(status_path, tpl)
        changed.append(str(status_path))

    # latest.json (mandatory)
    latest_path = Path("ops/reports/latest.json")
    if str(latest_path) in missing:
        tpl = load_template(LATEST_TEMPLATE)
        tpl["generated_at"] = now
        tpl["source"]["reason"] = "Placeholder created by Self-Healing (R3)"
        tpl["source"]["trigger"] = trigger
        write_json(latest_path, tpl)
        changed.append(str(latest_path))

    return {"changed_files": changed, "generated_at": now}
