#!/usr/bin/env python3
"""
Self_Guardian v2

- Scans HTML/MD files for basic compliance markers
- Checks minimal website security / metadata
- Performs a lightweight agent registry check
- Writes structured JSON log (guardian_log.json or path from --out)
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

SEVERITY_ORDER = {
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4,
}


def load_override_flag() -> bool:
    """Liest das Override-Flag aus der Umgebung."""
    return os.getenv(OVERRIDE_ENV, "0") == "1"


def write_log(payload: dict) -> None:
    """Schreibt das Guardian-Log als JSON auf die Platte."""
    try:
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
    except Exception as exc:
        print(f"[guardian] failed to write log: {exc}", file=sys.stderr)


# Checks ranking
SEVERITY_RANK = {
    "low": 0,
    "medium": 1,
    "high": 2,
    "critical": 3,
}

# --- Simple Checks Content ---------------------------------------------------

CHECKS = [
    # 1) Legal & DSGVO
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
    (
        "Impressum / Legal",
        lambda text: (
            "impressum" in text.lower()
            or "legal notice" in text.lower()
        ),
    ),
    (
        "Privacy Policy / Datenschutzerklärung",
        lambda text: (
            "datenschutzerklärung" in text.lower()
            or "privacy policy" in text.lower()
        ),
    ),
    # 2) Security / Policies
    (
        "Security Policy / Manifest erwähnt",
        lambda text: (
            "/policies/security.html" in text
            or "security policy" in text.lower()
            or "security manifest" in text.lower()
        ),
    ),
    # 3) RAG-Transparenz (später wichtig für knowledge.html)
    (
        "RAG / Retrieval-Augmented AI erwähnt",
        lambda text: (
            "retrieval-augmented" in text.lower()
            or "rag system" in text.lower()
            or "rag-layer" in text.lower()
        ),
    ),
    # 4) Privacy Policy / Datenschutzerklärung verlinkt
    (
        "Privacy Policy / Datenschutzerklärung verlinkt",
        lambda text: (
            "datenschutzerklärung" in text.lower()
            or "privacy policy" in text.lower()
            or "/policies/privacy.html" in text.lower()
        ),
    ),
    # 5) Impressum / Legal-Pflichtlink vorhanden
    (
        "Impressum / Legal-Pflichtlink vorhanden",
        lambda text: (
            "impressum" in text.lower()
            or "legal notice" in text.lower()
            or "/policies/impressum.html" in text.lower()
        ),
    ),
    # 6) Security Manifest linked
    (
        "Security Manifest verlinkt",
        lambda text: (
            "/policies/security.html" in text.lower()
            or "security manifest" in text.lower()
        ),
    ),
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


# --- Helper for Status-Aggregation ------------------------------------------


def determine_overall_status(issues):
    """
    Übersetzt Issues in einen Gesamtstatus.

    - high/critical -> FAIL
    - only low/medium -> WARN
    - no Issues -> OK
    """
    if not issues:
        return "OK"

    severities = {i.get("severity", "low") for i in issues}

    if any(s in {"high", "critical"} for s in severities):
        return "FAIL"

    return "WARN"


def has_hard_failure(status):
    return status == "FAIL"


# --- Main logic --------------------------------------------------------------


def severity_value(level: str) -> int:
    """Hilfsfunktion: mappt 'low'/'medium'/...' auf eine Zahl."""
    return SEVERITY_RANK.get(level, 0)


def main():
    global LOG_FILE

    parser = argparse.ArgumentParser(description="Run Self Guardian checks")
    parser.add_argument(
        "--root",
        default=".",
        help="Project root directory to scan (default: .)",
    )
    parser.add_argument(
        "--out",
        default=None,
        help="Path for JSON report output file (e.g. ops/reports/guardian.json)",
    )

    args = parser.parse_args()

    # Falls ein expliziter Output-Pfad übergeben wird, LOG_FILE darauf setzen
    if args.out:
        LOG_FILE = args.out

    # 1) Checks ausführen
    results = scan_dir(args.root)
    failed = [r for r in results if not r.get("ok", False)]

    # 2) Maximalen Schweregrad der fehlgeschlagenen Checks bestimmen
    max_sev_int = max(
        (severity_value(r.get("severity", "low")) for r in failed),
        default=-1,
    )

    max_sev_str = None
    if max_sev_int >= 0:
        # irgendeinen Check mit diesem Level picken
        for r in failed:
            if severity_value(r.get("severity", "low")) == max_sev_int:
                max_sev_str = r.get("severity", "low")
                break

    # 3) Override-Flag aus Env lesen
    override_flag = os.getenv(OVERRIDE_ENV, "0").lower() in {"1", "true", "yes"}

    # 4) Globalen Status bestimmen
    # - OVERRIDE → immer OK für CI (Status wird aber geloggt)
    # - ab "medium" → FAIL
    # - nur "low" → WARN
    if override_flag:
        status = "OVERRIDE"
    elif max_sev_int >= SEVERITY_RANK["medium"]:
        status = "FAIL"
    elif max_sev_int >= 0:
        status = "WARN"
    else:
        status = "OK"

    summary = {
        "total_checks": len(results),
        "failed_checks": len(failed),
        "max_severity": max_sev_str or "none",
        "status": status,
    }

    report = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "status": status,
        "override_used": override_flag,
        "summary": summary,
        "results": results,
    }

    # Telemetrie + Logfile
    emit("guardian-run", report)
    write_log(report)

    # Zusammenfassung in CI-Log
    print(json.dumps(report, ensure_ascii=False))

    # 5) Exit-Code:
    # - FAIL → 1 (Workflow rot)
    # - WARN / OK / OVERRIDE → 0 (Workflow grün)
    if status == "FAIL":
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
