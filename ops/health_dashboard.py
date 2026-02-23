#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List
from datetime import datetime

# ============================================================
# Phase 9 (SSOT Enforcement):
# - This script MUST NOT write any authoritative status.
# - It MUST NOT write to ops/status.json (deprecated pointer only).
# - It is READ-ONLY with respect to SSOT and generates a legacy HTML dashboard.
# ============================================================

OPS_DIR = Path(__file__).resolve().parent
REPORTS_DIR = OPS_DIR / "reports"

# Authoritative SSOT (read-only)
SSOT_FILE = REPORTS_DIR / "system_status.json"

# Non-authoritative logs / outputs
HEALTH_LOG = REPORTS_DIR / "health_log.jsonl"
OUTPUT_FILE = REPORTS_DIR / "health_dashboard.html"


def load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return default


def load_health_log(path: Path) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    if not path.exists():
        return records
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return records


def pct_01(value: float) -> int:
    """Convert 0..1 floats to % int."""
    try:
        return int(round(float(value) * 100))
    except Exception:
        return 0


def pct_any(value: Any) -> int:
    """
    Convert either:
      - 0..1 float -> %
      - 0..100 number -> %
    Heuristic: if > 1.5 treat as already percent scale.
    """
    try:
        v = float(value)
        if v > 1.5:
            return int(round(v))
        return int(round(v * 100))
    except Exception:
        return 0


def format_ts(ts: str | None) -> str:
    if not ts:
        return "–"
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return ts


def build_svg_autonomy(history: List[Dict[str, Any]], fallback_pct: int) -> str:
    """
    SVG line chart for autonomy.
    Prefers 'autonomy_level_estimate' (0..1) from health_log records.
    If history missing, shows single fallback point (from SSOT autonomy_level).
    """
    # Use up to 40 points
    data = history[-40:] if history else []

    values: List[float] = []
    for d in data:
        if "autonomy_level_estimate" in d:
            try:
                values.append(float(d.get("autonomy_level_estimate", 0.0)))
            except Exception:
                continue

    if not values:
        # Single fallback point derived ONLY from SSOT field
        # (still non-authoritative visualization, but deterministic)
        values = [max(0.0, min(1.0, fallback_pct / 100.0))]

    width, height, padding = 600, 200, 20
    max_y, min_y = 1.0, 0.0

    def x(i: int) -> float:
        if len(values) == 1:
            return padding
        return padding + i * (width - 2 * padding) / (len(values) - 1)

    def y(v: float) -> float:
        ratio = (v - min_y) / (max_y - min_y) if max_y != min_y else 0.0
        return height - padding - ratio * (height - 2 * padding)

    points = " ".join(f"{x(i)},{y(v)}" for i, v in enumerate(values))

    svg = f"""
<svg viewBox="0 0 {width} {height}" class="chart">
  <line x1="{padding}" y1="{height - padding}" x2="{width - padding}" y2="{height - padding}" class="axis"/>
  <line x1="{padding}" y1="{padding}" x2="{padding}" y2="{height - padding}" class="axis"/>

  <line x1="{padding}" y1="{y(0.0)}" x2="{width - padding}" y2="{y(0.0)}" class="grid"/>
  <line x1="{padding}" y1="{y(0.5)}" x2="{width - padding}" y2="{y(0.5)}" class="grid"/>
  <line x1="{padding}" y1="{y(1.0)}" x2="{width - padding}" y2="{y(1.0)}" class="grid"/>

  <polyline points="{points}" class="line"/>
  {"".join(f'<circle cx="{x(i)}" cy="{y(v)}" r="3" class="dot"/>' for i, v in enumerate(values))}
</svg>
"""
    return svg


def generate_dashboard() -> None:
    # READ-ONLY: load authoritative SSOT
    ssot: Dict[str, Any] = load_json(SSOT_FILE, default={}) or {}
    history = load_health_log(HEALTH_LOG)

    # Use SSOT fields if available (robust to schema evolution)
    # If SSOT missing, we still generate a dashboard, but clearly reflects missing truth.
    ssot_missing = not bool(ssot)
    autonomy_pct = pct_any(ssot.get("autonomy_level", 0))
    health_pct = pct_any(ssot.get("health_score", 0))

    generated_at = ssot.get("generated_at") or ssot.get("last_update") or None
    generated_at_fmt = format_ts(generated_at)

    svg_chart = build_svg_autonomy(history, fallback_pct=autonomy_pct)

    # legacy table from health_log (non-authoritative)
    table_rows = ""
    for rec in history[-20:][::-1]:
        ts = format_ts(rec.get("last_autonomous_action") or rec.get("ts"))
        a = pct_01(rec.get("autonomy_level_estimate", 0.0))
        s = pct_01(rec.get("agent_response_success_rate", 0.0))
        stab = pct_01(rec.get("system_stability_score", 0.0))
        errs = int(rec.get("self_detection_errors", 0) or 0)
        table_rows += f"""
      <tr>
        <td>{ts}</td>
        <td>{a}%</td>
        <td>{s}%</td>
        <td>{stab}%</td>
        <td>{errs}</td>
      </tr>
"""

    truth_badge = "TRUTH MISSING" if ssot_missing else "SSOT OK"
    truth_hint = (
        "SSOT file is missing or empty: ops/reports/system_status.json"
        if ssot_missing
        else "Source: ops/reports/system_status.json (authoritative)"
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>GEORGE Health Dashboard</title>
  <style>
    body {{
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #0b1020;
      color: #f5f5f5;
      margin: 0;
      padding: 24px;
    }}
    h1, h2 {{ margin-top: 0; }}
    .grid {{ stroke: #444; stroke-width: 1; stroke-dasharray: 4 4; }}
    .axis {{ stroke: #666; stroke-width: 1.5; }}
    .line {{ fill: none; stroke: #00e0ff; stroke-width: 2; }}
    .dot {{ fill: #00e0ff; }}
    .layout {{
      display: grid;
      grid-template-columns: 2fr 1.5fr;
      gap: 24px;
    }}
    .card {{
      background: #171c2f;
      border-radius: 16px;
      padding: 16px 20px;
      box-shadow: 0 10px 30px rgba(0,0,0,0.35);
    }}
    .pill {{
      display: inline-block;
      padding: 4px 10px;
      border-radius: 999px;
      font-size: 12px;
      background: #1f2937;
      color: #9ca3af;
    }}
    .kpi-main {{ font-size: 44px; font-weight: 700; }}
    .kpi-label {{ font-size: 14px; color: #9ca3af; }}
    .kpi-row {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
      margin-top: 12px;
    }}
    .kpi-card {{
      background: #111827;
      border-radius: 12px;
      padding: 10px 12px;
      font-size: 13px;
    }}
    .kpi-value {{ font-size: 18px; font-weight: 600; margin-top: 4px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
    th, td {{
      padding: 6px 8px;
      border-bottom: 1px solid #1f2937;
      text-align: left;
    }}
    th {{ color: #9ca3af; font-weight: 500; }}
    .chart {{ width: 100%; height: auto; margin-top: 8px; }}
    .warn {{ color: #fbbf24; }}
  </style>
</head>
<body>
  <h1>GEORGE Health Dashboard</h1>
  <p class="pill">virtauto.OS · Autonomy & System Health</p>
  <p class="pill">{truth_badge}</p>
  <p style="margin-top:10px;font-size:13px;color:#9ca3af;">
    {truth_hint} · Generated: {generated_at_fmt}
  </p>

  <div class="layout" style="margin-top:18px;">
    <div class="card">
      <div class="kpi-label">Autonomy (from SSOT)</div>
      <div class="kpi-main">{autonomy_pct}%</div>
      <div style="margin-top:14px;">
        <div class="kpi-label">Autonomy trend (health_log)</div>
        {svg_chart}
      </div>
      <p style="margin-top:12px;font-size:13px;color:#9ca3af;">
        Note: trend is derived from ops/reports/health_log.jsonl (non-authoritative).
      </p>
    </div>

    <div class="card">
      <h2 style="font-size:18px;margin-bottom:8px;">Key metrics (from SSOT)</h2>
      <div class="kpi-row">
        <div class="kpi-card">
          <div class="kpi-label">Health score</div>
          <div class="kpi-value">{health_pct}%</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label">SSOT state</div>
          <div class="kpi-value">{'OK' if not ssot_missing else '<span class="warn">MISSING</span>'}</div>
        </div>
      </div>
      <p style="margin-top:14px;font-size:13px;color:#9ca3af;">
        This dashboard does not write any status files.
        SSOT updates are produced by governed agents/workflows only.
      </p>
    </div>
  </div>

  <div class="card" style="margin-top:24px;">
    <h2 style="font-size:18px;margin-bottom:10px;">Recent health snapshots (health_log)</h2>
    <table>
      <thead>
        <tr>
          <th>Timestamp</th>
          <th>Autonomy</th>
          <th>Success</th>
          <th>Stability</th>
          <th>Self-Detection Errors</th>
        </tr>
      </thead>
      <tbody>
        {table_rows}
      </tbody>
    </table>
  </div>
</body>
</html>
"""

    OUTPUT_FILE.parent.mkdir(exist_ok=True, parents=True)
    OUTPUT_FILE.write_text(html, encoding="utf-8")
    print(f"[HealthDashboard] Wrote {OUTPUT_FILE}")


if __name__ == "__main__":
    # Phase 9: READ-ONLY. Do not write ops/status.json or any SSOT file here.
    generate_dashboard()
