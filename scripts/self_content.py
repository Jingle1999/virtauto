import argparse, json, os, textwrap, datetime as dt
from tools.ops.telemetry import emit

POSTS_DIR = "content/blog"

def draft_post(topic: str) -> dict:
    today = dt.date.today().isoformat()
    slug = topic.lower().replace(" ", "-")
    filename = f"{today}-{slug}.md"
    path = os.path.join(POSTS_DIR, filename)
    os.makedirs(POSTS_DIR, exist_ok=True)

    body = textwrap.dedent(f"""\
    ---
    title: "{topic}"
    date: "{today}"
    tags: ["virtauto", "industrial-ai", "agents"]
    description: "Autonomer Beitrag, generiert vom Self-Content-Agent."
    draft: true
    ---

    **TL;DR**: Platzhalter. Der Artikel wird durch Review-Gate/Editor verfeinert.

    ## Einleitung
    Kurzer Teaser …

    ## Hauptteil
    • Punkt 1  
    • Punkt 2

    ## Fazit
    …

    """)

    with open(path, "w", encoding="utf-8") as f:
        f.write(body)

    return {"path": path, "slug": slug, "title": topic}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--topic", required=False, default="Industrial MAS – Why Autonomy Matters")
    args = ap.parse_args()

    meta = draft_post(args.topic)
    emit("self_content.drafted", meta)

if __name__ == "__main__":
    main()
