from pathlib import Path
from tempfile import NamedTemporaryFile
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse

from .pipeline import run_pipeline

app = FastAPI(title="virtauto Local Decision Intelligence MVP", version="0.1.0")
CONFIG_PATH = Path("local_mvp/demo_config.yaml")
OUTPUT_DIR = Path("local_mvp/output")


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return """<!doctype html><html lang='de'><head><meta charset='utf-8'><title>virtauto MVP</title></head><body><h1>virtauto Decision Intelligence MVP</h1><form action='/analyse' method='post' enctype='multipart/form-data'><input type='file' name='file' accept='.csv' required><button type='submit'>CSV analysieren</button></form></body></html>"""


@app.post("/analyse")
async def analyse(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        return JSONResponse({"error": "Only CSV files are supported."}, status_code=400)
    with NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
        tmp.write(await file.read())
        tmp_path = Path(tmp.name)
    try:
        result = run_pipeline(tmp_path, CONFIG_PATH, OUTPUT_DIR)
        html = Path(result["paths"]["html"]).read_text(encoding="utf-8")
        return HTMLResponse(html)
    finally:
        tmp_path.unlink(missing_ok=True)


@app.get("/report.json")
def report_json():
    path = OUTPUT_DIR / "decision_report.json"
    if not path.exists():
        return JSONResponse({"error": "No report generated yet."}, status_code=404)
    return JSONResponse(content=__import__("json").loads(path.read_text(encoding="utf-8")))
