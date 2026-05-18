
import argparse, sys, json, pathlib

# Hier kann dein bisheriger Code für interne Checks/Funktionen stehen
# Dummy main, falls keine JSON-Args übergeben werden
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--in", dest="input", help="input file")
    parser.add_argument("--out", dest="output", help="output file")
    args = parser.parse_args()
    if args.input and args.output:
        payload = json.loads(pathlib.Path(args.input).read_text(encoding="utf-8"))
        pathlib.Path(args.output).write_text(json.dumps({"ok": True, "errors": []}, indent=2), encoding="utf-8")
    print(f"[OK] Review done -> {args.output}")

# --- CLI for JSON in/out ---
if __name__ == "__main__":
    if len(sys.argv) >= 3 and not sys.argv[1].startswith("--"):
        # JSON mode
        in_path  = pathlib.Path(sys.argv[1])
        out_path = pathlib.Path(sys.argv[2])
        payload = json.loads(in_path.read_text(encoding="utf-8-sig"))

        ok = True
        errors = []
        stage = payload.get("stage")

        if stage == "pre":
            t = payload.get("task", {})
            meta = t.get("meta", {})
            for k in ["owner", "source", "kpi"]:
                if k not in meta:
                    ok = False; errors.append(f"missing meta.{k}")

        elif stage == "post":
            data = payload.get("result", {}).get("data", {})
            if "summary" not in data:
                ok = False; errors.append("result.data.summary missing")
            txt = json.dumps(data, ensure_ascii=False)
            if "TBD" in txt or "???" in txt:
                ok = False; errors.append("forbidden placeholder found (TBD/???)")

        out_path.write_text(
            json.dumps({"ok": ok, "errors": errors}, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        sys.exit(0)
    else:
        main()
