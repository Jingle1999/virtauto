# monitoring/monitoring_agent.py
import os
import sys
import json
import datetime
import requests


def write_text(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def write_json(path: str, data: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def parse_args(argv):
    base_url = None
    output = None
    for i in range(len(argv)):
        if argv[i] == "--base-url" and i + 1 < len(argv):
            base_url = argv[i + 1]
        elif argv[i] == "--output" and i + 1 < len(argv):
            output = argv[i + 1]
    return base_url, output


def main():
    # CLI + ENV
    cli_base_url, output = parse_args(sys.argv)
    base_url = cli_base_url or os.getenv("BASE_URL") or "https://www.virtauto.de"
    output = output or "logs/agent_reports.md"
    telemetry_path = "ops/run_telemetry.json"

    # Ergebnis-Container
    now = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    telemetry = {
        "agent": "monitoring",
        "timestamp": now,
        "base_url": base_url,
        "status": "unknown",
        "http": {},
    }

    try:
        # Health-Check
        resp = requests.get(base_url, timeout=12)
        telemetry["http"] = {"code": resp.status_code, "ok": resp.ok}
        telemetry["status"] = "ok" if resp.ok else "degraded"

        # Markdown-Report
        report = []
        report.append(f"# Website Monitoring Report\n")
        report.append(f"- **Time**: {now}\n")
        report.append(f"- **URL**: {base_url}\n")
        report.append(f"- **HTTP**: {resp.status_code} ({'OK' if resp.ok else 'ERROR'})\n")
        write_text(output, "\n".join(report))

        # Telemetry JSON
        write_json(telemetry_path, telemetry)

        # Exitcode entsprechend Zustand
        if resp.ok:
            return 0
        else:
            return 1

    except Exception as e:
        telemetry["status"] = "error"
        telemetry["error"] = str(e)
        # Auch im Fehlerfall Artefakte schreiben
        write_text(
            output,
            f"# Website Monitoring Report\n- **Time**: {now}\n- **URL**: {base_url}\n- **ERROR**: {e}\n",
        )
        write_json(telemetry_path, telemetry)
        return 1


if __name__ == "__main__":
    sys.exit(main())
