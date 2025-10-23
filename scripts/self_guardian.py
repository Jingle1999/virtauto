import argparse, os, json, re
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
    os.makedirs(os.path.dirname(args.out), exist_ok=True)

    rep = scan_dir(args.root)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(rep, f, indent=2)

    emit("self_guardian.completed", {"report_path": args.out, "issues": rep["count"]})

if __name__ == "__main__":
    main()
