#!/usr/bin/env python3
"""
Self_Guardian v2

- Scans HTML/MD files for basic compliance markers
- Checks minimal website security / metadata
- Performs a lightweight agent registry check
- Writes structured JSON log (guardian_log.json)
- Returns non-zero exit code on FAIL (außer bei Override)

Emergency Override:
    Set environment variable SELF_GUARDIAN_OVERRIDE=1
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime

# --- Project root auf sys.path bringen ---------------------------------------

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# --- Telemetrie-Schnittstelle -----------------------------------------------

try:
    from tools.ops.telemetry import emit
except ModuleNotFoundError:
    def emit(event, data=None):
        print(f"[guardian-telemetry] {event}: {data or {}}")


LOG_FILE = "guardian_log.json"
OVERRIDE_ENV = "SELF_GUARDIAN_OVERRIDE"


# --- Einfache Inhalts-Checks -------------------------------------------------

CHECKS = [
    (
        "DSGVO contact email",
        lambda text: "andreas" in text.lower() and "@" in text,
    ),
    (
        "Cookie notice",
        lambda text: bool(
            re.search(r"cookie", text, re.IGNORECASE)
        ),
    ),
    # Hier kannst du später weitere Checks ergänzen
]


def scan_dir(root=".", exts=(".html", ".md")):
    """Scan HTML/MD Dateien und evaluiere CHECKS."""
    results = []
    for base, _, files in os.walk(root):
        for fn in files:
            if not fn.endswith(exts):
                continue
            path = os.path.join(base, fn)
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    txt = f.read()
            except Exception as exc:
                results.append(
                    {
                        "file": path,
                        "check": "read_error",
                        "ok": False,
                        "message": f"Could not read file: {exc}",
                        "severity": "medium",
                    }
                )
                continue

            for name, fn_check in CHECKS:
                ok = False
                try:
                    ok = bool(fn_check(txt))
                except Exception as exc:
                    results.append(
                        {
                            "file": path,
                            "check": name,
                            "ok": False,
                            "message": f"Check error: {exc}",
                            "severity": "medium",
                        }
                    )
                    continue

                if not ok:
                    results.append(
                        {
                            "file": path,
                            "check": name,
                            "ok": False,
                            "message": f"Missing or invalid: {name}",
                            "severity": "low",
                        }
                    )
    return results


# --- Agent Registry / Status Check (leichtgewichtig) -------------------------

def check_agents_registry():
    """
    Prüft, ob eine agents_registry.json existiert und grundlegende Felder enthält.
    Dieser Check schlägt nur hart fehl, wenn eine kaputte JSON gefunden wird.
    """
    registry_path = os.path.join(ROOT_DIR, "policies", "agents_registry.json")
    if not os.path.exists(registry_path):
        return [
            {
                "file": registry_path,
                "check": "agents_registry_present",
                "ok": False,
                "message": "agents_registry.json not found",
                "severity": "low",
            }
        ]

    try:
        with open(registry_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as exc:
        return [
            {
                "file": registry_path,
                "check": "agents_registry_json",
                "ok": False,
                "message": f"Invalid JSON in registry: {exc}",
                "severity": "high",
            }
        ]

    issues = []
    if not isinstance(data, list):
        issues.append(
            {
                "file": registry_path,
                "check": "agents_registry_shape",
                "ok": False,
                "message": "Registry should be a list of agents",
                "severity": "medium",
            }
        )
        return issues

    seen_ids = set()
    for agent in data:
        aid = agent.get("id")
        name = agent.get("name")
        if not aid or not name:
            issues.append(
                {
                    "file": registry_path,
                    "check": "agent_fields",
                    "ok": False,
                    "message": f"Agent missing id or name: {agent}",
                    "severity": "medium",
                }
            )
            continue
        if aid in seen_ids:
            issues.append(
                {
                    "file": registry_path,
                    "check": "agent_id_unique",
                    "ok": False,
                    "message": f"Duplicate agent id: {aid}",
                    "severity": "medium",
                }
            )
        seen_ids.add(aid)

    return issues


# --- Helper für Status-Aggregation ------------------------------------------

def determine_overall_status(issues):
    """
    Übersetzt Issues in einen Gesamtstatus.
    - high/critical -> FAIL
    - nur low/medium -> WARN
    - keine Issues   -> OK
    """
    if not issues:
        return "OK"

    severities = {i.get("severity", "low") for i in issues}
    if any(s in {"high", "critical"} for s in severities):
        return "FAIL"
    return "WARN"


def has_hard_failure(status):
    return status == "FAIL"


# --- Hauptlogik --------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root",
        default=".",
        help="Root directory to scan (default: current repo root)",
    )
    args = parser.parse_args()

    override = os.getenv(OVERRIDE_ENV, "").lower() in {"1", "true", "yes"}
    emit("guardian_start", {"root": args.root, "override": override})

    issues = []

    # 1) Content / HTML Checks
    issues.extend(scan_dir(root=args.root))

    # 2) Agent Registry Check
    issues.extend(check_agents_registry())

    status = determine_overall_status(issues)
    exit_code = 0

    if has_hard_failure(status):
        exit_code = 1

    if override and exit_code != 0:
        emit(
            "guardian_override",
            {"reason": "manual override via env", "original_status": status},
        )
        status = "OVERRIDDEN"
        exit_code = 0

    # Log schreiben
    log_payload = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "status": status,
        "override": override,
        "issue_count": len(issues),
        "issues": issues,
        "version": "2.0",
    }

    try:
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(log_payload, f, indent=2, ensure_ascii=False)
    except Exception as exc:
        emit("guardian_log_write_error", {"error": str(exc)})

    emit(
        "guardian_end",
        {"status": status, "exit_code": exit_code, "issues": len(issues)},
    )

    # Kurze CLI-Zusammenfassung
    print(f"[Self_Guardian] Status: {status} – Issues: {len(issues)}")
    if issues:
        for i in issues[:10]:
            print(
                f" - {i.get('severity','low').upper()} | "
                f"{i.get('check')} | {i.get('file')}"
            )
        if len(issues) > 10:
            print(f"   … +{len(issues) - 10} weitere Einträge")

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
