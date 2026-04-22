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
