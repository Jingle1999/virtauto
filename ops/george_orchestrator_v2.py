from datetime import datetime, timezone
import json
from pathlib import Path

def now_iso():
    return datetime.now(timezone.utc).isoformat()

def append_jsonl(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")

def save_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)

def handle_energy_scan_completed(event):
    data = event.get("data", {})
    saving_pct = float(data.get("saving_pct") or 0)
    data_confidence = data.get("data_confidence", "UNKNOWN")
    overall_traffic = data.get("overall_traffic", "UNKNOWN")
    cap_applied = bool(data.get("cap_applied", False))

    if data_confidence == "LOW":
        verdict = "BLOCK"
        action = "ESCALATE"
        reason = "Data confidence is LOW. Baseline validation required."

    elif overall_traffic == "RED":
        verdict = "BLOCK"
        action = "ESCALATE"
        reason = "Overall traffic is RED. Human review required."

    elif saving_pct < 2:
        verdict = "BLOCK"
        action = "REQUEST_BASELINE"
        reason = f"Saving potential below threshold: {saving_pct}%."

    elif cap_applied:
        verdict = "RECOMMEND"
        action = "SHAPE_LOAD"
        reason = "Saving potential reached benchmark cap. Shape load carefully."

    else:
        verdict = "RECOMMEND"
        action = "KEEP"
        reason = f"Energy scan completed with {saving_pct}% estimated saving potential."

    decision = {
        "ts": now_iso(),
        "decision_id": "DEC-" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S"),
        "event_type": event.get("type"),
        "scan_id": data.get("scan_id"),
        "verdict": verdict,
        "action": action,
        "reason": reason,
        "confidence": overall_traffic,
        "evidence": {
            "saving_pct": saving_pct,
            "data_confidence": data_confidence,
            "model_confidence": data.get("model_confidence"),
            "overall_traffic": overall_traffic,
            "cap_applied": cap_applied,
            "top_opportunities": data.get("top_opportunities", [])
        },
        "constraints": [
            "advisory_only",
            "operator_review_required",
            "no_autonomous_execution"
        ]
    }

    append_jsonl("ops/reports/decision_traces.jsonl", decision)
    save_json("ops/decisions/latest.json", decision)

    return decision