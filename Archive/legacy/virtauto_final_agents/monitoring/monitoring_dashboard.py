#!/usr/bin/env python3
import os, json, datetime as dt
from pathlib import Path

TELEMETRY = Path('logs/telemetry')
OUT = Path('monitoring/dashboard.json')
OUT.parent.mkdir(parents=True, exist_ok=True)

def main():
    events = []
    for fp in sorted(TELEMETRY.glob('*.jsonl')):
        for line in open(fp,'rb'):
            try:
                events.append(json.loads(line))
            except Exception:
                pass

    summary = {
        "updated_at": dt.datetime.utcnow().isoformat() + "Z",
        "events_total": len(events),
        "by_type": {}
    }
    for e in events:
        t = e.get("event_type","unknown")
        summary["by_type"][t] = summary["by_type"].get(t,0)+1

    OUT.write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print(f"Wrote {OUT}")

if __name__ == "__main__":
    main()
