#!/usr/bin/env python3
# Self-Validation for Guardian results
# Usage: python tools/self_validation.py ops/reports/guardian.json

import json, os, sys, hashlib, datetime as dt
from pathlib import Path

def load_json(p: Path, default):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return default

def main():
    if len(sys.argv) < 2:
        print("Usage: self_validation.py <guardian.json>", file=sys.stderr)
        sys.exit(2)

    src = Path(sys.argv[1]).resolve()
    reports_dir = Path("ops/reports")
    reports_dir.mkdir(parents=True, exist_ok=True)

    data = load_json(src, {"issues": []})

    # --- Severity Weights (env overrides -> defaults) ---
    W = {
        "critical": float(os.getenv("GV_WEIGHT_CRITICAL", "5")),
        "high":     float(os.getenv("GV_WEIGHT_HIGH",     "3")),
        "medium":   float(os.getenv("GV_WEIGHT_MEDIUM",   "2")),
        "low":      float(os.getenv("GV_WEIGHT_LOW",      "1")),
    }
    # Thresholds (fail/rollback) – env overrides -> defaults
    THRESH_FAIL      = float(os.getenv("GV_THRESH_FAIL",      "20"))
    THRESH_ROLLBACK  = float(os.getenv("GV_THRESH_ROLLBACK",  "35"))

    # Normalize issues list
    issues = data.get("issues", [])
    # Each issue is expected to carry: id, severity in {critical,high,medium,low}, rule, url, msg
    counts = {"critical":0,"high":0,"medium":0,"low":0}
    score_raw = 0.0
    for it in issues:
        sev = (it.get("severity") or "low").lower()
        if sev not in counts: sev = "low"
        counts[sev] += 1
        score_raw += W[sev]

    # Convert to 0..100 score where 100 = perfect (0 issues)
    # Simple exponential damping on raw score to avoid tiny changes near 100
    penalty = score_raw
    health  = max(0.0, 100.0 - min(90.0, penalty * 2.0))  # clamp

    status = "pass"
    action = "none"
    if penalty >= THRESH_ROLLBACK:
        status = "fail"
        action = "rollback"
    elif penalty >= THRESH_FAIL:
        status = "fail"
        action = "block"

    summary = {
        "timestamp_utc": dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "totals": {
            "issues_total": len(issues),
            **counts
        },
        "weights": W,
        "penalty": penalty,
        "health_score": round(health, 2),
        "status": status,           # pass | fail
        "recommended_action": action,  # none | block | rollback
        "source_sha": os.getenv("GITHUB_SHA", ""),
        "run_id": os.getenv("GITHUB_RUN_ID", "")
    }

    # Write machine outputs
    score_json = reports_dir / "guardian_score.json"
    score_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    # Write short human Markdown
    md = []
    md.append("# Guardian Self-Validation\n")
    md.append(f"- **Time (UTC):** {summary['timestamp_utc']}")
    md.append(f"- **Health Score:** {summary['health_score']}/100")
    md.append(f"- **Penalty:** {summary['penalty']}")
    md.append(f"- **Status:** **{summary['status'].upper()}**")
    md.append(f"- **Recommended Action:** **{summary['recommended_action']}**\n")
    md.append("## Issue Totals")
    for k in ("critical","high","medium","low"):
        md.append(f"- {k.capitalize()}: {counts[k]}")
    md.append("\n> Weights: " + ", ".join([f"{k}={v}" for k,v in W.items()]))
    (reports_dir / "self_validation.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    # Optional hash for provenance of the score
    h = hashlib.sha256(json.dumps(summary, sort_keys=True).encode("utf-8")).hexdigest()
    (reports_dir / "guardian_score.sha256").write_text(h + "\n", encoding="utf-8")

    # Expose outputs to GitHub Actions (GITHUB_OUTPUT)
    out_path = os.getenv("GITHUB_OUTPUT")
    if out_path:
        with open(out_path, "a", encoding="utf-8") as f:
            print(f"health_score={summary['health_score']}", file=f)
            print(f"status={summary['status']}", file=f)
            print(f"recommended_action={summary['recommended_action']}", file=f)
            print(f"penalty={summary['penalty']}", file=f)

    # Exit non-zero only if you want the job to fail on policy breach.
    # We keep it green and let downstream steps decide (deploy gate/rollback).
    print(json.dumps(summary, indent=2))
    sys.exit(0)

if __name__ == "__main__":
    main()
