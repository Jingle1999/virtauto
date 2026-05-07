import json
import sys
from pathlib import Path

from ops.george_energy_handler import handle_energy_scan_completed


def main():
    if len(sys.argv) < 2:
        print("Usage: python ops/run_energy_event.py path/to/energy_scan_completed.event.json")
        raise SystemExit(1)

    event_path = Path(sys.argv[1])

    with event_path.open("r", encoding="utf-8") as f:
        event = json.load(f)

    if event.get("type") != "energy/scan_completed":
        raise ValueError(f"Unsupported event type: {event.get('type')}")

    decision = handle_energy_scan_completed(event)

    print(json.dumps(decision, indent=2, ensure_ascii=False))
    print("\nSaved:")
    print("- ops/decisions/latest.json")
    print("- ops/reports/decision_traces.jsonl")


if __name__ == "__main__":
    main()
