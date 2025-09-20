
# --- am Ende von consistency_agent.py anhängen ---
if __name__ == "__main__":
    import sys, json, pathlib
    if len(sys.argv) < 3:
        print("Usage: python consistency_agent.py <input_json> <output_json>")
        sys.exit(2)
    in_path  = pathlib.Path(sys.argv[1])
    out_path = pathlib.Path(sys.argv[2])
    payload = json.loads(in_path.read_text(encoding="utf-8"))

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

    out_path.write_text(json.dumps({"ok": ok, "errors": errors}, ensure_ascii=False, indent=2), encoding="utf-8")
