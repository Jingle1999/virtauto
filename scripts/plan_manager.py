import argparse, json, os, sys, yaml
from datetime import datetime

GOALS = {
    "publish_blog_and_audit": [
        # nutzt deine bestehenden Events / Workflows in korrekter Reihenfolge
        {"id": "content_ingest", "tool": "repo_dispatch",
         "params": {"event_type": "self_ingest"}, "depends_on": []},
        {"id": "review_gate", "tool": "repo_dispatch",
         "params": {"event_type": "self_review"}, "depends_on": ["content_ingest"]},
        {"id": "design_gate", "tool": "repo_dispatch",
         "params": {"event_type": "self_design"}, "depends_on": ["review_gate"]},
        {"id": "site_audit", "tool": "repo_dispatch",
         "params": {"event_type": "self_audit"}, "depends_on": ["design_gate"],
         "success_criteria": ["telemetry.last_audit_score >= 0.90"]},
        {"id": "deploy", "tool": "workflow_dispatch",
         "params": {"workflow_file": "site-deploy.yml", "ref": "main"}, "depends_on": ["site_audit"]}
    ]
}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--goal", required=True)
    ap.add_argument("--registry", default="ops/tool_registry.yaml")
    ap.add_argument("--out", default="ops/current_plan.json")
    args = ap.parse_args()

    if not os.path.exists(args.registry):
        print(f"Registry not found: {args.registry}", file=sys.stderr)
        sys.exit(2)

    with open(args.registry, "r", encoding="utf-8") as f:
        registry = {t["name"]: t for t in yaml.safe_load(f)}

    if args.goal not in GOALS:
        print(f"Unknown goal: {args.goal}", file=sys.stderr)
        sys.exit(2)

    # validate tools against registry
    steps = []
    for s in GOALS[args.goal]:
        tool = s["tool"]
        if tool not in registry:
            print(f"Tool not in registry: {tool}", file=sys.stderr)
            sys.exit(2)
        steps.append(s)

    plan = {
        "meta": {
            "created_at": datetime.utcnow().isoformat() + "Z",
            "goal": args.goal,
            "schema": "v1"
        },
        "steps": steps
    }

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)
    print(f"Wrote plan to {args.out}")

if __name__ == "__main__":
    main()
