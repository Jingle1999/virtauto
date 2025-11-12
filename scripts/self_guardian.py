import argparse, os, json, re
import sys
from tools.ops.telemetry import emit

CHECKS = [
    ("DSGVO contact email", lambda text: "andreas.braun@virtauto.de" in text),
    ("Cookie notice",       lambda text: re.search(r"cookie|datenschutz", text, re.I) is not None),
]

def scan_dir(root=".", exts=(".html", ".md")) -> dict:
    results = []
    for base, _, files in os.walk(root):
        for fn in files:
            if fn.endswith(exts):
                p = os.path.join(base, fn)
                try:
                    txt = open(p, "r", encoding="utf-8").read()
                except Exception:
                    continue
                probs = []
                for name, fnc in CHECKS:
                    if not fnc(txt):
                        probs.append(name)
                if probs:
                    results.append({"path": p, "missing": probs})
    return {"issues": results, "count": len(results)}
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default="ops/reports/guardian.json")
    args = ap.parse_args()

    # Stelle sicher, dass das Zielverzeichnis existiert
    os.makedirs(os.path.dirname(args.out), exist_ok=True)

    # (Beispiel) Checks laufen lassen – ersetze ggf. durch deine echte Logik
    result = scan_dir(root=args.root, exts=(".html", ".md"))
    report = {
        "status": "ok" if result["count"] == 0 else "issues",
        "timestamp": "auto",
        "checked": ["workflow configs", "file health"],
        **result
    }

    # Report schreiben
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"guardian report saved to {args.out}")

    # Exit-Code: 0 = OK, 2 = Findings -> Workflow rot
    has_issues = len(report.get("issues", [])) > 0
    print(f"guardian outcome: {'issues' if has_issues else 'ok'}")
    sys.exit(2 if has_issues else 0)


if __name__ == "__main__":
    main()
