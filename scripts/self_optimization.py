import argparse, json, os, re
from tools.ops.telemetry import emit

FIXES_DIR = "ops/fixes"
PR_SUMMARY = "chore(self-opt): automated tweaks (seo/perf/design)"

def propose_tweaks() -> list[dict]:
    """
    Lies einfache Heuristiken und schlage kleine Änderungen vor,
    z.B. <img> ohne alt, fehlende <meta>, zu große Bilder, etc.
    """
    suggestions = []
    web_root = "virtauto_website" if os.path.isdir("virtauto_website") else "."

    # Beispiel: fehlende <meta name="description">
    index_html = os.path.join(web_root, "index.html")
    if os.path.exists(index_html):
        with open(index_html, "r", encoding="utf-8") as f:
            html = f.read()
        if 'name="description"' not in html:
            suggestions.append({
                "path": index_html,
                "action": "insert_meta_description",
                "description": "Add meta description for SEO"
            })

    emit("self_optimize.proposed", {"count": len(suggestions)})
    return suggestions

def write_patch_files(suggestions: list[dict]) -> str:
    os.makedirs(FIXES_DIR, exist_ok=True)
    plan_path = os.path.join(FIXES_DIR, "plan.json")
    with open(plan_path, "w", encoding="utf-8") as f:
        json.dump({"pr_title": PR_SUMMARY, "changes": suggestions}, f, indent=2)
    emit("self_optimize.plan_written", {"path": plan_path})
    return plan_path

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(FIXES_DIR, "plan.json"))
    args = ap.parse_args()

    suggestions = propose_tweaks()
    plan_path = write_patch_files(suggestions)
    emit("self_optimize.completed", {"plan_path": plan_path})

if __name__ == "__main__":
    main()
