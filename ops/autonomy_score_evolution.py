#!/usr/bin/env python3
import json
from pathlib import Path
from datetime import datetime

OPS = Path(__file__).resolve().parent
DEC_SNAP = OPS / "decisions" / "snapshots"
HEALTH_LOG = OPS / "reports" / "health_log.jsonl"

def load_health_series():
    series = []
    if not HEALTH_LOG.exists():
        return series
    for line in HEALTH_LOG.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            series.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return series

def load_snapshots():
    snaps = []
    if not DEC_SNAP.exists():
        return snaps
    for p in sorted(DEC_SNAP.glob("*.json")):
        try:
            snaps.append(json.loads(p.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            continue
    return snaps

def clamp(x): 
    return max(0.0, min(1.0, x))

def main():
    health = load_health_series()
    snaps = load_snapshots()

    # Map date -> last health entry that day (best-effort)
    health_by_date = {}
    for h in health:
        ts = h.get("timestamp") or h.get("last_updated")
        if not ts:
            continue
        d = ts.split("T")[0]
        health_by_date[d] = h

    rows = []
    for s in snaps:
        date = s.get("date")
        total = int(s.get("total_decisions", 0))
        succ = int(s.get("successful", 0))
        fail = int(s.get("failed", 0))
        blocked = 0
        by_agent = s.get("by_agent", {}) or {}
        for a, st in by_agent.items():
            blocked += int(st.get("blocked", 0))

        executed = succ + fail
        exec_rate = (succ / executed) if executed else 0.0
        coverage = (executed / total) if total else 0.0

        h = health_by_date.get(date, {})
        stability = h.get("system_stability_score")
        if stability is None:
            # fallback: use exec_rate but penalize blocks slightly
            stability = clamp(exec_rate * (1.0 - 0.1*blocked))

        score = clamp(0.45*exec_rate + 0.35*coverage + 0.20*float(stability))

        rows.append({
            "date": date,
            "total": total,
            "executed": executed,
            "success": succ,
            "fail": fail,
            "blocked": blocked,
            "execution_rate": round(exec_rate, 3),
            "coverage": round(coverage, 3),
            "stability": round(float(stability), 3),
            "autonomy_score": round(score, 3),
        })

    out = OPS / "reports" / "autonomy_score_evolution.json"
    out.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print(f"Wrote {out} with {len(rows)} rows.")

if __name__ == "__main__":
    main()
