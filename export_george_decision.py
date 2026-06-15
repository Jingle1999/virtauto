import json
from pathlib import Path

SOURCE = Path("decision_traces/george_trace.jsonl")
TARGET = Path("src/pages/george_decision.json")

if not SOURCE.exists():
    raise FileNotFoundError(f"Missing source trace: {SOURCE}")

lines = [
    line.strip()
    for line in SOURCE.read_text().splitlines()
    if line.strip()
]

if not lines:
    raise ValueError("GEORGE trace is empty")

latest = json.loads(lines[-1])

TARGET.parent.mkdir(parents=True, exist_ok=True)
TARGET.write_text(json.dumps(latest, indent=2))

print(f"Exported latest GEORGE decision to {TARGET}")
print(json.dumps(latest, indent=2))