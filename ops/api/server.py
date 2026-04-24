from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import json
import tempfile
from pathlib import Path

from ops.runtime.decision_runtime_v1 import run_decision

app = FastAPI(title="virtauto Decision API", version="0.1.0")


class DecisionInput(BaseModel):
    line_id: str
    time_window: str
    energy_price_tier: str
    buffer_fill_level: int
    quality_posture: str
    oee_posture: str
    candidate_shiftable_stages: list[str]


DEMO_SCENARIO = {
    "line_id": "TVL",
    "time_window": "08:30",
    "energy_price_tier": "high",
    "buffer_fill_level": 5,
    "quality_posture": "ok",
    "oee_posture": "ok",
    "candidate_shiftable_stages": ["stage_2", "stage_4"],
}


def _business_decision_label(gate_verdict: str) -> tuple[str, str]:
    if gate_verdict == "ALLOW_ADVISORY":
        return "Verschieben empfohlen", "grün"
    if gate_verdict == "BLOCK":
        return "Nicht verschieben", "rot"
    return "Noch nicht verschieben", "gelb"


def _translate_reason(reason: str) -> str:
    translations = {
        "Quality posture not admissible": "Die Qualitätslage ist nicht stabil genug. Qualität hat Vorrang vor Energiekosten.",
        "OEE posture not admissible": "Die Produktionsstabilität ist nicht ausreichend. OEE hat Vorrang vor Energiekosten.",
        "Insufficient buffer": "Der Puffer reicht nicht aus. Eine Verschiebung könnte den Produktionsfluss gefährden.",
        "Geo station is protected": "Eine geschützte Station wäre betroffen. Diese Station darf nicht automatisch verschoben werden.",
        "Energy price high, bounded delay admissible": "Die Energiepreise sind hoch, die Linie läuft stabil und der Puffer reicht aus.",
        "No admissible optimization opportunity": "Es gibt aktuell keinen ausreichenden Anlass für eine Verschiebung.",
    }
    return translations.get(reason, reason)


def build_business_demo_response(runtime_output: dict) -> dict:
    result = runtime_output["result"]
    gate = runtime_output["gate"]
    contract = runtime_output["contract"]
    inputs = contract["inputs"]
    label, status = _business_decision_label(gate["gate_verdict"])
    recommendation = result.get("recommendation")

    if recommendation:
        stages = ", ".join(recommendation["targets"])
        action = f"{stages} bis zu {recommendation['max_delay_minutes']} Minuten verschieben"
    else:
        action = "Keine Verschiebung auslösen"

    return {
        "demo_title": "Energy Peak Mitigation",
        "business_question": "Soll ein Produktionsschritt bei hohem Energiepreis kurz verschoben werden?",
        "decision": label,
        "status": status,
        "plain_summary": (
            f"{_translate_reason(gate['reason'])} "
            "virtauto empfiehlt deshalb eine begrenzte, nachvollziehbare Maßnahme — ohne automatische Ausführung."
            if gate["gate_verdict"] == "ALLOW_ADVISORY"
            else f"{_translate_reason(gate['reason'])} virtauto empfiehlt deshalb keine Verschiebung."
        ),
        "recommended_action": {
            "what": action,
            "why": "Lastspitze reduzieren, ohne Qualität oder Produktionsstabilität zu gefährden",
            "mode": "Empfehlung, keine automatische Ausführung",
        },
        "situation": {
            "line": inputs["line_id"],
            "time_window": inputs["time_window"],
            "energy_price": "hoch" if inputs["energy_price_tier"] == "high" else inputs["energy_price_tier"],
            "buffer_level": inputs["buffer_fill_level"],
            "quality": "stabil" if inputs["quality_posture"] == "ok" else "auffällig",
            "oee": "stabil" if inputs["oee_posture"] == "ok" else "auffällig",
        },
        "safety_checks": [
            {"check": "Qualität", "result": "stabil" if inputs["quality_posture"] == "ok" else "nicht stabil"},
            {"check": "OEE / Produktionsstabilität", "result": "stabil" if inputs["oee_posture"] == "ok" else "nicht stabil"},
            {"check": "Puffer", "result": "ausreichend" if inputs["buffer_fill_level"] >= 3 else "zu niedrig"},
            {"check": "Geschützte Stationen", "result": "nicht betroffen" if "stage_3" not in inputs["candidate_shiftable_stages"] else "betroffen"},
        ],
        "tradeoff": "Energiekosten dürfen reduziert werden, solange Qualität und Produktionsstabilität nicht gefährdet werden.",
        "owner": "Produktionsleitung",
        "veto": "Qualität",
        "traceability": {
            "decision_id": result["decision_id"],
            "trace_id": result["trace_id"],
            "execution_mode": result["execution_mode"],
        },
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/decision/latest")
def latest_decision():
    latest_path = Path("ops/decisions/latest.json")
    if not latest_path.exists():
        raise HTTPException(status_code=404, detail="latest.json not found")

    with latest_path.open("r", encoding="utf-8") as f:
        return json.load(f)


@app.post("/decision/run")
def decision_run(payload: DecisionInput):
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as tmp:
        json.dump(payload.model_dump(), tmp, ensure_ascii=False, indent=2)
        tmp_path = tmp.name

    try:
        output = run_decision(tmp_path)
        return output
    finally:
        Path(tmp_path).unlink(missing_ok=True)


@app.post("/decision/run/demo")
def decision_run_demo(payload: DecisionInput | None = None):
    """Run the energy decision scenario and return a business-readable demo response."""
    demo_payload = payload.model_dump() if payload else DEMO_SCENARIO

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as tmp:
        json.dump(demo_payload, tmp, ensure_ascii=False, indent=2)
        tmp_path = tmp.name

    try:
        output = run_decision(tmp_path)
        return build_business_demo_response(output)
    finally:
        Path(tmp_path).unlink(missing_ok=True)
