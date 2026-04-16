import json
import uuid
import datetime
import os

# -----------------------------
# Helpers
# -----------------------------

def now():
    return datetime.datetime.utcnow().isoformat() + "Z"

def load_json(path):
    with open(path, "r") as f:
        return json.load(f)

def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def append_trace(path, record):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(record) + "\n")


# -----------------------------
# Context Builder
# -----------------------------

def build_context(event):
    return {
        "line_id": event["line_id"],
        "time_window": event["time_window"],
        "state_hash": str(uuid.uuid4())[:8],
        "snapshot_time": now()
    }


# -----------------------------
# Decision Contract
# -----------------------------

def create_decision_contract(event, context):
    decision_id = f"dec_{context['line_id']}_{uuid.uuid4().hex[:6]}"
    trace_id = f"trace_{uuid.uuid4().hex[:6]}"

    return {
        "decision_id": decision_id,
        "trace_id": trace_id,
        "use_case": "energy_peak_mitigation",
        "intent": "reduce_peak_energy_cost",
        "scope": {
            "line_id": context["line_id"],
            "time_window": context["time_window"]
        },
        "context_ref": {
            "state_hash": context["state_hash"],
            "snapshot_time": context["snapshot_time"]
        },
        "inputs": event,
        "constraints_applied": [
            "geo_station_protected",
            "quality_over_cost",
            "takt_stability_required",
            "advisory_only"
        ],
        "candidate_action": {
            "type": "delay_stage_groups",
            "targets": event["candidate_shiftable_stages"],
            "max_delay_minutes": 15
        },
        "authority_scope": "production_lead",
        "veto_scope": "quality",
        "risk_class": "low",
        "execution_mode": "PROPOSE_ONLY",
        "created_at": now()
    }


# -----------------------------
# Authority Resolver (minimal)
# -----------------------------

def resolve_authority(contract):
    return {
        "owner": contract["authority_scope"],
        "veto": contract["veto_scope"],
        "allowed_execution_modes": ["PROPOSE_ONLY"],
        "authority_ok": True
    }


# -----------------------------
# Gate Evaluator
# -----------------------------

def evaluate_gate(contract):
    inputs = contract["inputs"]

    # RULES
    if inputs["quality_posture"] != "ok":
        return ("HOLD", "Quality posture not admissible")

    if inputs["oee_posture"] != "ok":
        return ("HOLD", "OEE posture not admissible")

    if inputs["buffer_fill_level"] < 3:
        return ("HOLD", "Insufficient buffer")

    if "stage_3" in contract["candidate_action"]["targets"]:
        return ("BLOCK", "Geo station is protected")

    if inputs["energy_price_tier"] == "high":
        return ("RECOMMEND", "Energy price high, bounded delay admissible")

    return ("HOLD", "No optimization opportunity")


# -----------------------------
# Result Builder
# -----------------------------

def build_result(contract, authority, gate_verdict, reason):
    status = gate_verdict

    result = {
        "decision_id": contract["decision_id"],
        "trace_id": contract["trace_id"],
        "status": status,
        "gate_verdict": gate_verdict,
        "summary": reason,
        "action": contract["candidate_action"] if status == "RECOMMEND" else None,
        "owner": authority["owner"],
        "veto": authority["veto"],
        "execution_mode": contract["execution_mode"],
        "emitted_at": now()
    }

    return result


# -----------------------------
# Trace Writer
# -----------------------------

def write_trace(contract, result):
    record = {
        "trace_id": contract["trace_id"],
        "decision_id": contract["decision_id"],
        "timestamp": now(),
        "status": result["status"],
        "summary": result["summary"]
    }

    append_trace("ops/traces/decision_trace.jsonl", record)


# -----------------------------
# Main Runtime
# -----------------------------

def run_decision(input_path):
    event = load_json(input_path)

    context = build_context(event)
    contract = create_decision_contract(event, context)
    authority = resolve_authority(contract)
    verdict, reason = evaluate_gate(contract)
    result = build_result(contract, authority, verdict, reason)

    # Save artifacts
    contract_path = f"ops/decisions/contracts/{contract['decision_id']}.json"
    result_path = f"ops/decisions/results/{contract['decision_id']}.json"

    save_json(contract_path, contract)
    save_json(result_path, result)
    save_json("ops/decisions/latest.json", result)
    save_json("ops/decisions/gate_result.json", {"verdict": verdict})

    write_trace(contract, result)

    print("\n--- DECISION RESULT ---")
    print(json.dumps(result, indent=2))


# -----------------------------
# CLI
# -----------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    args = parser.parse_args()

    run_decision(args.input)