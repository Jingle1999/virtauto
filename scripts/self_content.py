#!/usr/bin/env python3
"""
Self Content Agent

Simple content-draft generator for virtauto.de.

Called from the GitHub Actions workflow `self-content.yml` like:

  python -m scripts.self_content \
      --topic "Industrial MAS – Why Autonomy Matters" \
      --root . \
      --out content/drafts

What it does (for now):
- parses CLI arguments (topic, root, out)
- creates the output directory if needed
- generates a timestamped markdown draft with basic front-matter
- prints the created file path (for debugging)

You can later extend `generate_body()` to actually call an LLM.
"""

import argparse
import datetime as dt
import os
from pathlib import Path
import textwrap


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Self Content Agent – draft generator")
    parser.add_argument(
        "--topic",
        "-t",
        required=True,
        help="Topic or working title for the draft (used as title + in slug).",
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Repository root (used as base path when resolving --out).",
    )
    parser.add_argument(
        "--out",
        default="content/drafts",
        help="Relative path (from --root) where the draft markdown should be written.",
    )
    return parser.parse_args()


def slugify(text: str) -> str:
    text = text.strip().lower()
    repl = {
        "ä": "ae",
        "ö": "oe",
        "ü": "ue",
        "ß": "ss",
        "–": "-",
        "—": "-",
        " ": "-",
        "/": "-",
        "\\": "-",
        ":": "",
        ";": "",
        ",": "",
        ".": "",
        "?": "",
        "!": "",
        "\"": "",
        "'": "",
        "(": "",
        ")": "",
    }
    for src, dst in repl.items():
        text = text.replace(src, dst)
    # nur erlaubte Zeichen
    return "".join(c for c in text if c.isalnum() or c == "-")


def generate_body(topic: str) -> str:
    """
    Placeholder body – hier kannst du später echten AI-Content einbauen.
    Für jetzt nur ein kurzes Template, das deutlich macht, dass der Self Content
    Agent gearbeitet hat.
    """
    return textwrap.dedent(
        f"""
        # {topic}

        _Draft created automatically by the **Self Content Agent**._

        This is an initial scaffold for an article on:

        **{topic}**

        Next steps:
        - Enrich this draft with real content (MAS, Industrial AI, virtauto.OS, etc.)
        - Review language, structure and add visuals
        - Publish via the regular virtauto content workflow

        <!-- TODO: Replace this placeholder with AI-generated insights. -->
        """
    ).lstrip()


def main() -> None:
    args = parse_args()

    root = Path(args.root).resolve()
    out_dir = root / args.out
    out_dir.mkdir(parents=True, exist_ok=True)

    now = dt.datetime.utcnow()
    date_str = now.strftime("%Y-%m-%d")
    ts_str = now.strftime("%Y%m%d-%H%M%S")

    slug = slugify(args.topic)
    filename = f"{date_str}-{slug}.md"
    out_path = out_dir / filename

    front_matter = textwrap.dedent(
        f"""\
        ---
        title: "{args.topic}"
        date: {date_str}
        draft: true
        agent: self_content
        slug: {slug}
        ---

        """
    )

    body = generate_body(args.topic)

    with out_path.open("w", encoding="utf-8") as f:
        f.write(front_matter)
        f.write(body)

    print(f"[Self Content Agent] Draft written to: {out_path}")


if __name__ == "__main__":
    main()
