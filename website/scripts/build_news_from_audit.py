import json, os, datetime, subprocess

# Input: data/audit.ldjson
# Output: website/data/news.json, website/data/build.json

data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
audit_file = os.path.join(data_dir, "audit.ldjson")
news_file = os.path.join(data_dir, "news.json")
build_file = os.path.join(data_dir, "build.json")

# 1. Audit -> News
news = []
if os.path.exists(audit_file):
    with open(audit_file, "r") as f:
        for line in f:
            try:
                event = json.loads(line)
                news.append({
                    "ts": event.get("ts"),
                    "event": event.get("event"),
                    "details": str(event.get("details"))
                })
            except:
                continue
news = news[-50:]

with open(news_file, "w") as f:
    json.dump(news, f, indent=2)

# 2. Build Info
def git(cmd):
    try:
        return subprocess.check_output(cmd, shell=True).decode().strip()
    except:
        return None

build = {
    "commit": git("git rev-parse --short HEAD"),
    "branch": git("git rev-parse --abbrev-ref HEAD"),
    "time": datetime.datetime.utcnow().isoformat() + "Z"
}

with open(build_file, "w") as f:
    json.dump(build, f, indent=2)
