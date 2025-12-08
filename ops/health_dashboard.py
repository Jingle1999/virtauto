#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List
from datetime import datetime

# Basis-Pfade
OPS_DIR = Path(__file__).resolve().parent
REPORTS_DIR = OPS_DIR / "reports"

STATUS_FILE = OPS_DIR / "status.json"
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


def pct(value: float) -> int:
    try:
        return int(round(float(value) * 100))
    except Exception:
        return 0


def format_ts(ts: str | None) -> str:
    if not ts:
        return "–"
    # falls ISO, kurz formatieren
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return ts


def build_svg_autonomy(history: List[Dict[str, Any]]) -> str:
    """Ein kleines SVG-Linechart für autonomy_level_estimate."""
    if not history:
        return "<p>No autonomy history yet.</p>"

    # max 40 Punkte
    data = history[-40:]
    values = [float(d.get("autonomy_level_estimate", 0.0)) for d in data]
    if not values:
        return "<p>No autonomy data.</p>"

    width, height, padding = 600, 200, 20
    max_y = 1.0
    min_y = 0.0

    def x(i: int) -> float:
        if len(values) == 1:
            return padding
        return padding + i * (width - 2 * padding) / (len(values) - 1)

    def y(v: float) -> float:
        # 0 unten, 1 oben
        ratio = (v - min_y) / (max_y - min_y) if max_y != min_y else 0.0
        return height - padding - ratio * (height - 2 * padding)

    points = " ".join(f"{x(i)},{y(v)}" for i, v in enumerate(values))

    svg = f"""
<svg viewBox="0 0 {width} {height}" class="chart">
  <!-- Achsen -->
  <line x1="{padding}" y1="{height - padding}" x2="{width - padding}" y2="{height - padding}" class="axis"/>
  <line x1="{padding}" y1="{padding}" x2="{padding}" y2="{height - padding}" class="axis"/>

  <!-- 0%, 50%, 100% Linien -->
  <line x1="{padding}" y1="{y(0.0)}" x2="{width - padding}" y2="{y(0.0)}" class="grid"/>
  <line x1="{padding}" y1="{y(0.5)}" x2="{width - padding}" y2="{y(0.5)}" class="grid"/>
  <line x1="{padding}" y1="{y(1.0)}" x2="{width - padding}" y2="{y(1.0)}" class="grid"/>

  <polyline points="{points}" class="line"/>

  <!-- Punkte -->
  {"".join(f'<circle cx="{x(i)}" cy="{y(v)}" r="3" class="dot"/>' for i, v in enumerate(values))}
</svg>
"""
    return svg


def generate_dashboard() -> None:
    status = load_json(STATUS_FILE, default={}) or {}
    history = load_health_log(HEALTH_LOG)

    current_autonomy = pct(status.get("autonomy_level_estimate", 0.5))
    current_success = pct(status.get("agent_response_success_rate", 0.0))
    stability = pct(status.get("system_stability_score", 0.0))
    self_errors = int(status.get("self_detection_errors", 0))
    last_action = format_ts(status.get("last_autonomous_action"))
    total_actions = int(status.get("total_actions", 0))
    failed_actions = int(status.get("failed_actions", 0))

    svg_chart = build_svg_autonomy(history)

    # letzte 20 Einträge für Tabelle
    table_rows = ""
    for rec in history[-20:][::-1]:
        ts = format_ts(rec.get("last_autonomous_action"))
        a = pct(rec.get("autonomy_level_estimate", 0.0))
        s = pct(rec.get("agent_response_success_rate", 0.0))
        stab = pct(rec.get("system_stability_score", 0.0))
        errs = int(rec.get("self_detection_errors", 0))
        table_rows += f"""
      <tr>
        <td>{ts}</td>
        <td>{a}%</td>
        <td>{s}%</td>
        <td>{stab}%</td>
        <td>{errs}</td>
      </tr>
"""

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
    h1, h2 {{
      margin-top: 0;
    }}
    .grid {{
      stroke: #444;
      stroke-width: 1;
      stroke-dasharray: 4 4;
    }}
    .axis {{
      stroke: #666;
      stroke-width: 1.5;
    }}
    .line {{
      fill: none;
      stroke: #00e0ff;
      stroke-width: 2;
    }}
    .dot {{
      fill: #00e0ff;
    }}
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
    .kpi-main {{
      font-size: 44px;
      font-weight: 700;
    }}
    .kpi-label {{
      font-size: 14px;
      color: #9ca3af;
    }}
    .kpi-row {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 12px;
      margin-top: 12px;
    }}
    .kpi-card {{
      background: #111827;
      border-radius: 12px;
      padding: 10px 12px;
      font-size: 13px;
    }}
    .kpi-value {{
      font-size: 18px;
      font-weight: 600;
      margin-top: 4px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
    }}
    th, td {{
      padding: 6px 8px;
      border-bottom: 1px solid #1f2937;
      text-align: left;
    }}
    th {{
      color: #9ca3af;
      font-weight: 500;
    }}
    .chart {{
      width: 100%;
      height: auto;
      margin-top: 8px;
    }}
  </style>
</head>
<body>
  <h1>GEORGE Health Dashboard</h1>
  <p class="pill">virtauto.OS &middot; Autonomy &amp; System Health</p>

  <div class="layout" style="margin-top:18px;">
    <div class="card">
      <div class="kpi-label">Estimated autonomy level</div>
      <div class="kpi-main">{current_autonomy}%</div>
      <div style="margin-top:4px;font-size:13px;color:#9ca3af;">
        Actions: {total_actions} total &middot; {failed_actions} failed
      </div>
      <div style="margin-top:6px;font-size:13px;color:#9ca3af;">
        Last autonomous action: {last_action}
      </div>
      <div style="margin-top:14px;">
        <div class="kpi-label">Autonomy trend (last runs)</div>
        {svg_chart}
      </div>
    </div>

    <div class="card">
      <h2 style="font-size:18px;margin-bottom:8px;">Key metrics</h2>
      <div class="kpi-row">
        <div class="kpi-card">
          <div class="kpi-label">Agent success rate</div>
          <div class="kpi-value">{current_success}%</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label">System stability</div>
          <div class="kpi-value">{stability}%</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label">Self-detection errors</div>
          <div class="kpi-value">{self_errors}</div>
        </div>
      </div>
      <p style="margin-top:14px;font-size:13px;color:#9ca3af;">
        Autonomy is a blend of success rate and stability. Self-detection errors lower
        both stability and autonomy level.
      </p>
    </div>
  </div>

  <div class="card" style="margin-top:24px;">
    <h2 style="font-size:18px;margin-bottom:10px;">Recent health snapshots</h2>
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
    generate_dashboard()
