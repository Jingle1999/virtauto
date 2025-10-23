vimport argparse, json, os, sys, time
import requests
from collections import defaultdict, deque

GITHUB_API = "https://api.github.com"

def topo_order(steps):
    incoming = defaultdict(int)
    graph = defaultdict(list)
    by_id = {s["id"]: s for s in steps}
    for s in steps:
        for d in s.get("depends_on", []):
            graph[d].append(s["id"])
            incoming[s["id"]] += 1
    q = deque([sid for sid in by_id if incoming[sid] == 0])
    order = []
    while q:
        u = q.popleft()
        order.append(by_id[u])
        for v in graph[u]:
            incoming[v] -= 1
            if incoming[v] == 0:
                q.append(v)
    if len(order) != len(steps):
        raise RuntimeError("Cycle detected in plan")
    return order

def repo_dispatch(owner, repo, token, event_type):
    url = f"{GITHUB_API}/repos/{owner}/{repo}/dispatches"
    r = requests.post(url, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json"
    }, json={"event_type": event_type})
    r.raise_for_status()
    return True

def workflow_dispatch(owner, repo, token, workflow_file, ref="main"):
    url = f"{GITHUB_API}/repos/{owner}/{repo}/actions/workflows/{workflow_file}/dispatches"
    r = requests.post(url, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json"
    }, json={"ref": ref})
    r.raise_for_status()
    return True

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", default="ops/current_plan.json")
    args = ap.parse_args()

    if not os.path.exists(args.plan):
        print(f"Plan file not found: {args.plan}", file=sys.stderr)
        sys.exit(2)

    with open(args.plan, "r", encoding="utf-8") as f:
        plan = json.load(f)

    steps = plan["steps"]
    order = topo_order(steps)

    repo_full = os.getenv("GITHUB_REPOSITORY")  # e.g. Jingle1999/virtauto
    token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
    if not repo_full or not token:
        print("Missing GITHUB_REPOSITORY or GITHUB_TOKEN", file=sys.stderr)
        sys.exit(2)
    owner, repo = repo_full.split("/")

    telemetry = {"executed": []}

    for s in order:
        sid = s["id"]; tool = s["tool"]; params = s.get("params", {})
        print(f"==> Executing {sid} [{tool}] with {params}")
        ok = False
        try:
            if tool == "repo_dispatch":
                ok = repo_dispatch(owner, repo, token, params["event_type"])
            elif tool == "workflow_dispatch":
                ok = workflow_dispatch(owner, repo, token, params["workflow_file"], params.get("ref", "main"))
            elif tool == "noop":
                ok = True
            else:
                raise RuntimeError(f"Unknown tool: {tool}")
        except Exception as e:
            print(f"[ERROR] step {sid}: {e}", file=sys.stderr)
            ok = False

        telemetry["executed"].append({"id": sid, "tool": tool, "ok": ok, "ts": time.time()})
        if not ok:
            print(f"Plan aborted at {sid}", file=sys.stderr)
            break

        # kurze Abstände, da nachgelagerte Waits in GEORGE existieren
        time.sleep(1)

    os.makedirs("ops/telemetry", exist_ok=True)
    with open("ops/telemetry/last_plan_run.json", "w", encoding="utf-8") as f:
        json.dump(telemetry, f, indent=2)
    print("Telemetry written to ops/telemetry/last_plan_run.json")

if __name__ == "__main__":
    main()
