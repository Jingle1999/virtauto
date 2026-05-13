import argparse
import datetime
import hashlib
import json
import os
from typing import Any, Dict, Tuple


# -----------------------------
# Helpers
# -----------------------------

def now() -> str:
    return datetime.datetime.now(datetime.UTC).isoformat().replace("+00:00", "Z")


def load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: str, data: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def append_trace(path: str, record: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def stable_hash(data: Dict[str, Any]) -> str:
    payload = json.dumps(data, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]


# -----------------------------
# Context Builder
# -----------------------------

def build_context(event: Dict[str, Any]) -> Dict[str, Any]:
    event_hash = stable_hash(event)
    return {
        "line_id": event["line_id"],
        "time_window": event["time_window"],
        "state_hash": event_hash,
        "snapshot_time": now(),
    }


# -----------------------------
# Decision Contract
# -----------------------------

def create_decision_contract(event: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    decision_suffix = stable_hash(
        {
            "use_case": "energy_peak_mitigation",
            "line_id": context["line_id"],
            "time_window": context["time_window"],
            "inputs": event,
        }
    )

    decision_id = f"dec_{context['line_id'].lower()}_{decision_suffix}"
    trace_id = f"trace_{decision_suffix}"

    return {
        "decision_id": decision_id,
        "trace_id": trace_id,
        "use_case": "energy_peak_mitigation",
        "intent": "reduce_peak_energy_cost",
        "scope": {
            "line_id": context["line_id"],
            "time_window": context["time_window"],
        },
        "context_ref": {
            "state_hash": context["state_hash"],
            "snapshot_time": context["snapshot_time"],
        },
        "inputs": event,
        "constraints_applied": [
            "geo_station_protected",
            "quality_over_cost",
            "takt_stability_required",
            "advisory_only",
        ],
        "candidate_action": {
            "type": "delay_stage_groups",
            "targets": event["candidate_shiftable_stages"],
            "max_delay_minutes": 15,
        },
        "authority_scope": "production_lead",
        "veto_scope": "quality",
        "risk_class": "low",
        "decision_class": "operational",
        "execution_mode": "PROPOSE_ONLY",
        "created_at": now(),
    }


# -----------------------------
# Authority Resolver (minimal)
# -----------------------------

def resolve_authority(contract: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "owner": contract["authority_scope"],
        "veto": contract["veto_scope"],
        "allowed_execution_modes": ["PROPOSE_ONLY"],
        "authority_ok": True,
        "resolved_at": now(),
    }


# -----------------------------
# Gate Evaluator
# -----------------------------

def evaluate_gate(contract: Dict[str, Any]) -> Tuple[str, str]:
    inputs = contract["inputs"]

    if inputs["quality_posture"] != "ok":
        return ("HOLD", "Quality posture not admissible")

    if inputs["oee_posture"] != "ok":
        return ("HOLD", "OEE posture not admissible")

    if inputs["buffer_fill_level"] < 3:
        return ("HOLD", "Insufficient buffer")

    if "stage_3" in contract["candidate_action"]["targets"]:
        return ("BLOCK", "Geo station is protected")

    if inputs["energy_price_tier"] == "high":
        return ("ALLOW_ADVISORY", "Energy price high, bounded delay admissible")

    return ("HOLD", "No admissible optimization opportunity")


# -----------------------------
# Result Builder
# -----------------------------

def build_result(
    contract: Dict[str, Any],
    authority: Dict[str, Any],
    gate_verdict: str,
    reason: str,
) -> Dict[str, Any]:
    if gate_verdict == "ALLOW_ADVISORY":
        lifecycle_status = "completed"
        recommendation = contract["candidate_action"]
    elif gate_verdict in ("HOLD", "BLOCK", "ESCALATE"):
        lifecycle_status = "completed"
        recommendation = None
    else:
        lifecycle_status = "error"
        recommendation = None

    return {
        "decision_id": contract["decision_id"],
        "trace_id": contract["trace_id"],
        "use_case": contract["use_case"],
        "decision_class": contract["decision_class"],
        "status": lifecycle_status,
        "gate_verdict": gate_verdict,
        "summary": reason,
        "recommendation": recommendation,
        "owner": authority["owner"],
        "veto": authority["veto"],
        "execution_mode": contract["execution_mode"],
        "line_id": contract["scope"]["line_id"],
        "time_window": contract["scope"]["time_window"],
        "emitted_at": now(),
    }


# -----------------------------
# Trace Writer
# -----------------------------

def write_trace(contract: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
    record = {
        "trace_id": contract["trace_id"],
        "decision_id": contract["decision_id"],
        "timestamp": now(),
        "use_case": contract["use_case"],
        "decision_class": contract["decision_class"],
        "line_id": contract["scope"]["line_id"],
        "time_window": contract["scope"]["time_window"],
        "status": result["status"],
        "gate_verdict": result["gate_verdict"],
        "summary": result["summary"],
        "recommendation": result["recommendation"],
        "constraints_applied": contract["constraints_applied"],
        "execution_mode": contract["execution_mode"],
    }

    append_trace("ops/reports/decision_trace.jsonl", record)
    save_json("ops/reports/decision_trace.json", record)
    return record


# -----------------------------
# Main Runtime
# -----------------------------

def run_decision(input_path: str) -> Dict[str, Any]:
    event = load_json(input_path)

    context = build_context(event)
    contract = create_decision_contract(event, context)
    authority = resolve_authority(contract)
    gate_verdict, reason = evaluate_gate(contract)
    result = build_result(contract, authority, gate_verdict, reason)
    trace_record = write_trace(contract, result)

    contract_path = f"ops/decisions/contracts/{contract['decision_id']}.json"
    result_path = f"ops/decisions/results/{contract['decision_id']}.json"
    latest_path = "ops/decisions/latest.json"
    gate_path = "ops/decisions/gate_result.json"

    save_json(contract_path, contract)
    save_json(result_path, result)
    save_json(latest_path, result)
    save_json(
        gate_path,
        {
            "decision_id": contract["decision_id"],
            "trace_id": contract["trace_id"],
            "gate_verdict": gate_verdict,
            "reason": reason,
            "written_at": now(),
        },
    )

    return {
        "contract": contract,
        "authority": authority,
        "gate": {
            "gate_verdict": gate_verdict,
            "reason": reason,
        },
        "result": result,
        "trace": trace_record,
        "artifacts": {
            "contract_path": contract_path,
            "result_path": result_path,
            "latest_path": latest_path,
            "gate_path": gate_path,
            "trace_json_path": "ops/reports/decision_trace.json",
            "trace_jsonl_path": "ops/reports/decision_trace.jsonl",
        },
    }


# -----------------------------
# CLI
# -----------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    args = parser.parse_args()

    output = run_decision(args.input)

    print("\n--- DECISION RESULT ---")
    print(json.dumps(output["result"], indent=2, ensure_ascii=False))
    print("\n--- ARTIFACTS ---")
    print(json.dumps(output["artifacts"], indent=2, ensure_ascii=False))
