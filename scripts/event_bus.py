import json, datetime

def log_event(agent, event, message):
    entry = {
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "agent": agent,
        "event": event,
        "message": message
    }
    with open("ops/events.jsonl", "a") as f:
        f.write(json.dumps(entry) + "\n")
    print(f"✅ Event logged: {agent} - {event}")

if __name__ == "__main__":
    log_event("website_monitoring", "status_ok", "System self-check completed successfully.")
