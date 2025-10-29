# monitoring/monitoring_agent.py
import argparse
import json
import os
import time
from datetime import datetime

import requests


def ensure_dirs():
    os.makedirs("logs", exist_ok=True)
    os.makedirs("ops", exist_ok=True)
    os.makedirs("tests", exist_ok=True)


def check_site(url: str, timeout: float = 10.0) -> dict:
    t0 = time.perf_counter()
    try:
        resp = requests.get(
            url,
            timeout=timeout,
            headers={"User-Agent": "virtauto-monitor/1.0"},
            allow_redirects=True,
        )
        dt_ms = int((time.perf_counter() - t0) * 1000)
        ok = 200 <= resp.status_code < 400
        return {
            "ok": ok,
            "status_code": resp.status_code,
            "elapsed_ms": dt_ms,
            "error": None,
        }
    except Exception as e:
        dt_ms = int((time.perf_counter() - t0) * 1000)
        return {
            "ok": False,
            "status_code": None,
            "elapsed_ms": dt_ms,
            "error": str(e),
        }


def write_report_md(path_md: str, base_url: str, result: dict) -> None:
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    lines = [
        f"# Website Monitoring Report",
        f"- **Time**: {ts}",
        f"- **URL**: {base_url}",
        f"- **OK**: {result['ok']}",
        f"- **HTTP**: {result['status_code']}",
        f"- **Elapsed**: {result['elapsed_ms']} ms",
    ]
    if result["error"]:
        lines.append(f"- **Error**: `{result['error']}`")
    with open(path_md, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def write_telemetry_json(path_json: str, base_url: str, result: dict) -> None:
    payload = {
        "timestamp": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "base_url": base_url,
        "ok": result["ok"],
        "status_code": result["status_code"],
        "elapsed_ms": result["elapsed_ms"],
        "error": result["error"],
        "agent": "website-monitoring",
        "version": "1.0",
    }
    with open(path_json, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def main():
    parser = argparse.ArgumentParser(description="virtauto website monitoring agent")
    parser.add_argument(
        "--base-url",
        dest="base_url",
        default=os.environ.get("BASE_URL", "https://www.virtauto.de"),
        help="Target URL to check",
    )
    parser.add_argument(
        "--output",
        dest="output_md",
        default="logs/agent_reports.md",
        help="Path for markdown report",
    )
    args = parser.parse_args()

    base_url = args.base_url.strip()
    output_md = args.output_md

    ensure_dirs()

    result = check_site(base_url)
    # Reports
    write_report_md(output_md, base_url, result)
    write_telemetry_json("ops/run_telemetry.json", base_url, result)

    # Exit code tells GitHub Actions pass/fail
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
