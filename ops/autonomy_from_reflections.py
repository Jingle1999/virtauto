import json, os, glob
from datetime import datetime, timezone

REFL_DIR = "ops/decisions/reflections"
OUT_FILE = "ops/reports/autonomy_from_reflections.json"
AUTONOMY_FILE = "ops/autonomy.json"

def clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def safe_get(d, path, default=None):
    cur = d
    for p in path:
        if not isinstance(cur, dict) or p not in cur:
            return default
        cur = cur[p]
    return cur

def impact_score(refl: dict) -> float:
    status = safe_get(refl, ["decision_ref", "status"], "unknown")
    risk = safe_get(refl, ["guardian_ref", "risk_level"], "low")

    non_blocking = safe_get(refl, ["metrics", "autonomy_signal", "non_blocking"], True)
    self_heal = safe_get(refl, ["metrics", "autonomy_signal", "self_heal_attempted"], False)
    human_required = safe_get(refl, ["metrics", "autonomy_signal", "human_required"], False)
    policy_violation = safe_get(refl, ["metrics", "autonomy_signal", "policy_violation"], False)

    q_clarity = safe_get(refl, ["reflection", "decision_quality", "clarity"], 0.5)
    q_safety = safe_get(refl, ["reflection", "decision_quality", "safety"], 0.5)
    q_rev = safe_get(refl, ["reflection", "decision_quality", "reversibility"], 0.5)
    q_avg = (q_clarity + q_safety + q_rev) / 3.0

    s = 0.0
    # positives
    s += 0.05 if non_blocking else 0.0
    s += 0.05 if not human_required else 0.0
    s += 0.05 if not policy_violation else 0.0
    s += 0.10 * (q_avg - 0.5) * 2.0  # map 0.5->0, 1.0->+0.10, 0.0->-0.10

    if self_heal and status == "success":
        s += 0.10

    # negatives
    if status != "success":
        s -= 0.10
    if risk == "high":
        s -= 0.10
    if policy_violation:
        s -= 0.25
    if human_required:
        s -= 0.10

    # clamp impact to [-1, +1]
    return max(-1.0, min(1.0, s))

def main(window_size=20, alpha=0.05):
    os.makedirs(os.path.dirname(OUT_FILE), exist_ok=True)

    files = sorted(glob.glob(os.path.join(REFL_DIR, "reflection_*.json")))
    recent = files[-window_size:] if len(files) > window_size else files

    impacts = []
    successes = 0
    human_req = 0
    policy_viol = 0
    q_vals = []

    for fp in recent:
        r = load_json(fp)
        impacts.append(impact_score(r))

        if safe_get(r, ["decision_ref", "status"]) == "success":
            successes += 1
        if safe_get(r, ["metrics", "autonomy_signal", "human_required"], False):
            human_req += 1
        if safe_get(r, ["metrics", "autonomy_signal", "policy_violation"], False):
            policy_viol += 1

        q = safe_get(r, ["reflection", "decision_quality"], None)
        if isinstance(q, dict):
            q_avg = (q.get("clarity", 0.5) + q.get("safety", 0.5) + q.get("reversibility", 0.5)) / 3.0
            q_vals.append(q_avg)

    mean_impact = sum(impacts) / len(impacts) if impacts else 0.0
    success_rate = successes / len(recent) if recent else 0.0
    human_rate = human_req / len(recent) if recent else 0.0
    avg_q = sum(q_vals) / len(q_vals) if q_vals else 0.5

    # current autonomy from ops/autonomy.json (fallback 0.5)
    try:
        a = load_json(AUTONOMY_FILE)
        current = float(safe_get(a, ["overview", "system_autonomy_level"], 0.5))
    except Exception:
        current = 0.5

    new_val = clamp(current + alpha * mean_impact, 0.0, 1.0)
    delta = new_val - current
    trend = "up" if delta > 0.0001 else ("down" if delta < -0.0001 else "flat")

    out = {
        "schema_version": "1.0",
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "window_size": len(recent),
        "alpha": alpha,
        "current_autonomy": round(new_val, 4),
        "delta": round(delta, 4),
        "trend": trend,
        "signals": {
            "success_rate": round(success_rate, 4),
            "policy_violations": policy_viol,
            "human_required_rate": round(human_rate, 4),
            "avg_decision_quality": round(avg_q, 4),
            "mean_impact": round(mean_impact, 4)
        }
    }

    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)

if __name__ == "__main__":
    main()
