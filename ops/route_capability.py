#!/usr/bin/env python3
import json
import os
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAP_GRAPH = ROOT / "capabilities" / "capability_graph.json"
SYSTEM_STATUS = ROOT / "ops" / "reports" / "system_status.json"
TRACE_PATH = ROOT / "ops" / "reports" / "failover_trace.jsonl"

def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def load_json(p: Path):
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)

def safe_get(d, path, default=None):
    cur = d
    for k in path:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur

def agent_health(status: dict, agent_id: str):
    """
    Deterministic health extraction:
    - Prefer agents.<id>.health_score or agents.<id>.health (0..1)
    - Else derive from state/status (ACTIVE => 1.0, PLANNED/MANUAL/UNKNOWN => 0.5, FAIL/DOWN => 0.0)
    """
    a = safe_get(status, ["agents", agent_id], {}) or {}
    for key in ["health_score", "health", "score"]:
        v = a.get(key, None)
        try:
            if v is not None:
                n = float(v)
                if 0.0 <= n <= 1.0:
                    return n
        except Exception:
            pass

    st = str(a.get("state", a.get("status", "UNKNOWN"))).upper()
    if st in ["ACTIVE", "OK", "GREEN", "ONLINE"]:
        return 1.0
    if st in ["PLANNED", "MANUAL", "SUPERVISED", "UNKNOWN", "IN_PROGRESS", "MVP"]:
        return 0.5
    if st in ["FAIL", "FAILED", "DOWN", "CRITICAL", "ISSUE", "RED"]:
        return 0.0
    return 0.5

def append_trace(evt: dict):
    TRACE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with TRACE_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(evt, ensure_ascii=False) + "\n")

def main():
    capability = os.environ.get("CAPABILITY", "deploy").strip()

    graph = load_json(CAP_GRAPH)
    status = load_json(SYSTEM_STATUS)

    cap = safe_get(graph, ["registry", capability])
    if not cap:
        raise SystemExit(f"Capability '{capability}' not found in {CAP_GRAPH}")

    routing = cap.get("routing", {}) or {}
    threshold = float(routing.get("health_threshold", 0.8))

    agents = cap.get("agents", [])
    primary = next((a for a in agents if a.get("role") == "primary"), None)
    secondary = next((a for a in agents if a.get("role") == "secondary"), None)
    if not primary or not secondary:
        raise SystemExit("Capability must define primary and secondary agent.")

    primary_id = primary["id"]
    secondary_id = secondary["id"]

    primary_health = agent_health(status, primary_id)

    # Deterministic routing rule:
    # IF primary_health < threshold => route secondary, else route primary
    if primary_health < threshold:
        selected = secondary_id
        selected_role = "secondary"
        reason = "primary_health_below_threshold"
    else:
        selected = primary_id
        selected_role = "primary"
        reason = "primary_healthy"

    evt = {
        "ts": now_iso(),
        "capability": capability,
        "event": "FAILOVER_ROUTE",
        "route": {
            "selected_agent": selected,
            "role": selected_role,
            "primary": primary_id,
            "secondary": secondary_id
        },
        "reason": reason,
        "inputs": {
            "primary_health": primary_health,
            "threshold": threshold
        },
        "result": "OK"
    }
    append_trace(evt)

    # GitHub Actions outputs (via stdout)
    # - selected_agent: which agent GEORGE routed to
    # - selected_role: primary/secondary
    # - deploy_workflow: which workflow file to execute next
    deploy_workflow = "site-deploy.yml" if selected_role == "primary" else "site-deploy-backup.yml"
    print(f"selected_agent={selected}")
    print(f"selected_role={selected_role}")
    print(f"deploy_workflow={deploy_workflow}")

if __name__ == "__main__":
    main()