import json, time, uuid, pathlib, os

LOG_DIR = pathlib.Path(os.environ.get("VIRTAUTO_LOG_DIR", str(pathlib.Path.cwd() / "virtauto_logs")))
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "audit.ldjson"

def audit(event: str, details):
    rec = {"ts": time.time(), "event": event, "details": details, "id": str(uuid.uuid4())}
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\\n")
    return rec["id"]
