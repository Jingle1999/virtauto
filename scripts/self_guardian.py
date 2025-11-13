import argparse
import os
import json
import re

from tools.ops.telemetry import emit


CHECKS = [
    ("DSGVO contact email", lambda text: "andreas.braun@virtauto.de" in text),
    ("Cookie notice",      lambda text: re.search(r"cookie|datenschutz", text, re.I) is not None),
    # Hier kannst du später weitere Checks ergänzen
]


def scan_dir(root=".", exts=(".html", ".md")) -> dict:
    results = []
    for base, _, files in os.walk(root):
        for fn in files:
            if not fn.endswith(exts):
                continue
            path = os.path.join(base, fn)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    txt = f.read()
            except Exception:
                continue

            missing = [name for name, fn_check in CHECKS if not fn_check(txt)]
            if missing:
                results.append({"path": path, "missing": missing})

    return {"issues": results, "count": len(results)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default="ops/reports/guardian.json")
    args = ap.parse_args()

    # Zielverzeichnis anlegen
    os.makedirs(os.path.dirname(args.out), exist_ok=True)

    result = scan_dir(root=args.root, exts=(".html", ".md"))
    report = {
        "status": "ok" if result["count"] == 0 else "issues",
        "timestamp": "auto",
        "checked": ["policy text", "cookie notice"],
        "issues": result["issues"],
    }

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"Guardian report saved to {args.out}")
    emit("guardian.scan", report)


if __name__ == "__main__":
    main()
