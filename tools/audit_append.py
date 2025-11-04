#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Append audit entries with hash chaining (append-only JSON Lines).
Usage:
  python tools/audit_append.py ops/reports/guardian.json ops/audit_chain.yaml
"""

import os, sys, json, hashlib, datetime
from typing import Any, Dict

try:
    import yaml  # PyYAML (ist in deinem Repo-Setup i.d.R. schon vorhanden)
except Exception:
    print("ERROR: PyYAML is required (pip install pyyaml)", file=sys.stderr)
    sys.exit(2)


def sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def iso_utc_now() -> str:
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def read_last_hash(log_path: str, anchor_path: str) -> str:
    """
    Liefert den sha_previous:
      - letzte Zeile aus audit.log -> sha_current
      - sonst Inhalt aus Anchor-Datei (falls vorhanden)
      - sonst Hash von leerem String
    """
    if os.path.isfile(log_path):
        with open(log_path, "r", encoding="utf-8") as f:
            lines = [ln.strip() for ln in f if ln.strip()]
        if lines:
            try:
                last = json.loads(lines[-1])
                return last.get("sha_current") or ""
            except Exception:
                pass

    if os.path.isfile(anchor_path):
        with open(anchor_path, "r", encoding="utf-8") as f:
            return sha256(f.read().strip())

    return sha256("")  # Fallback


def ensure_parent(path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)


def load_guardian_report(path: str) -> Dict[str, Any]:
    if not os.path.isfile(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except Exception:
            return {}


def main():
    if len(sys.argv) < 3:
        print("Usage: audit_append.py <guardian_report.json> <audit_chain.yaml>", file=sys.stderr)
        sys.exit(2)

    report_path = sys.argv[1]
    chain_cfg   = sys.argv[2]

    with open(chain_cfg, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    alg          = (cfg.get("integrity") or {}).get("algorithm", "SHA256")
    if alg.upper() != "SHA256":
        print("ERROR: Only SHA256 is supported right now.", file=sys.stderr)
        sys.exit(2)

    anchor_file  = (cfg.get("integrity") or {}).get("anchor_file", "status/audit_anchor.txt")
    audit_log    = (cfg.get("storage")   or {}).get("audit_log", "status/audit.log")
    fields       = cfg.get("fields") or []
    ensure_parent(audit_log)
    ensure_parent(anchor_file)

    # Anchor-Datei initial anlegen, falls nicht vorhanden
    if not os.path.isfile(anchor_file):
        with open(anchor_file, "w", encoding="utf-8") as f:
            f.write("virtauto_audit_anchor_v1\n")

    # Guardian Report laden
    rep = load_guardian_report(report_path)
    issues = rep.get("issues") or []

    # Metadaten
    agent_name = rep.get("agent", "self_guardian")
    run_id = os.environ.get("GITHUB_RUN_ID") or os.environ.get("CI_RUN_ID") or "local"

    appended = 0
    sha_prev = read_last_hash(audit_log, anchor_file)

    # Wenn der Report keine Issues enthält, optional einen "no-issues" Eintrag schreiben
    if not issues:
        entry = {
            "timestamp":  iso_utc_now(),
            "agent":      agent_name,
            "rule_id":    "guardian:no_issues",
            "severity":   "info",
            "description":"No policy violations detected",
            "source":     rep.get("url") or "n/a",
            "run_id":     run_id,
            "sha_previous": sha_prev,
        }
        # Hash deterministisch über die bestellte Felderliste
        material = "|".join(str(entry.get(k, "")) for k in fields if k not in ("sha_current",))
        entry["sha_current"] = sha256(material)

        with open(audit_log, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        appended += 1
    else:
        # Für jedes Issue einen Eintrag anfügen
        for it in issues:
            e = {
                "timestamp":  iso_utc_now(),
                "agent":      agent_name,
                "rule_id":    it.get("id") or it.get("rule_id") or "unknown_rule",
                "severity":   (it.get("severity") or "info").lower(),
                "description": it.get("message") or it.get("desc") or "n/a",
                "source":     it.get("source") or rep.get("url") or "n/a",
                "run_id":     run_id,
                "sha_previous": sha_prev,
            }
            material = "|".join(str(e.get(k, "")) for k in fields if k not in ("sha_current",))
            e["sha_current"] = sha256(material)

            with open(audit_log, "a", encoding="utf-8") as f:
                f.write(json.dumps(e, ensure_ascii=False) + "\n")

            sha_prev = e["sha_current"]  # Chain fortsetzen
            appended += 1

    print(f"Appended {appended} audit entrie(s) to {audit_log}")


if __name__ == "__main__":
    main()
