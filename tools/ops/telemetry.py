
from __future__ import annotations
import os, uuid, time, socket, getpass
from datetime import datetime, timezone
import orjson as json

TELEMETRY_DIR = os.getenv("TELEMETRY_DIR", "logs/telemetry")
os.makedirs(TELEMETRY_DIR, exist_ok=True)

def emit(event_type: str, payload: dict, run_id: str | None = None) -> str:
    """
    Schreibt einen JSONL-Eintrag gem. ops/telemetry_schema.json.
    Gibt die event_id zurück.
    """
    event_id = str(uuid.uuid4())
    doc = {
        "event_id": event_id,
        "event_type": event_type,           # z.B. 'self_audit.completed'
        "ts": datetime.now(timezone.utc).isoformat(),
        "run_id": run_id or os.getenv("GITHUB_RUN_ID") or str(uuid.uuid4()),
        "actor": getpass.getuser(),
        "host": socket.gethostname(),
        "context": {
            "repo": os.getenv("GITHUB_REPOSITORY"),
            "sha": os.getenv("GITHUB_SHA"),
            "ref": os.getenv("GITHUB_REF"),
            "workflow": os.getenv("GITHUB_WORKFLOW"),
            "job": os.getenv("GITHUB_JOB"),
        },
        "payload": payload,                 # frei, aber bitte schema-konform halten
    }
    path = os.path.join(TELEMETRY_DIR, f"{int(time.time())}.jsonl")
    with open(path, "ab") as f:
        f.write(json.dumps(doc))
        f.write(b"\n")
    return event_id
