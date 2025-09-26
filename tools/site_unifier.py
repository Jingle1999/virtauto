#!/usr/bin/env python3
import os
import re
import argparse
from pathlib import Path

CSS_LINK = '<link rel="stylesheet" href="assets/styles_unify.css">'
IMG_CLASS = 'img-responsive'
FIGURE_CLASS = 'media'

def add_css_link(html: str) -> (str, bool):
    if 'assets/styles_unify.css' in html:
        return html, False
    # insert before </head>
    new = re.sub(r'</head>', f'  {CSS_LINK}\n</head>', html, flags=re.IGNORECASE, count=1)
    changed = (new != html)
    return (new if changed else html), changed

def normalize_img_tags(html: str) -> (str, int):
    """
    - ensure loading=lazy decoding=async
    - ensure class includes IMG_CLASS
    - remove inline width/height styles; keep width/height attributes if present
    - add alt if missing (fallback from file name)
    - wrap with <figure class="media"> if not already inside figure
    """
    count = 0

    def repl(m):
        nonlocal count
        tag = m.group(0)

        # skip data URI svgs
        if 'data:image' in tag:
            return tag

        # add loading/decoding
        if ' loading=' not in tag:
            tag = tag[:-1] + ' loading="lazy">'
        if ' decoding=' not in tag:
            tag = tag[:-1] + ' decoding="async">'

        # class handling
        if ' class=' in tag:
            tag = re.sub(r'class="([^"]*)"', lambda c: f'class="{ensure_class(c.group(1), IMG_CLASS)}"', tag)
        else:
            tag = tag[:-1] + f' class="{IMG_CLASS}">'

        # alt
        if ' alt=' not in tag:
            src = re.search(r'src="([^"]+)"', tag)
            alt = (Path(src.group(1)).stem.replace('-', ' ').replace('_', ' ') if src else 'image')
            tag = tag[:-1] + f' alt="{alt}">'

        # remove inline width/height styles (style="...")
        tag = re.sub(r'style="[^"]*?(width|height)\s*:[^"]*"', lambda _: re.sub(r'style="[^"]*"', '', tag), tag)

        count += 1
        return tag

    def ensure_class(current: str, needed: str) -> str:
        parts = set(filter(None, re.split(r'\s+', current.strip())))
        parts.add(needed)
        return ' '.join(sorted(parts))

    new_html = re.sub(r'<img\b[^>]*?>', repl, html, flags=re.IGNORECASE)
    # Wrap orphan <img> in figure blocks if not already inside <figure>
    new_html = re.sub(
        r'(?<!<figure[^>]*>\s*)(<img\b[^>]*?>)',
        lambda m: f'<figure class="{FIGURE_CLASS}">{m.group(1)}</figure>',
        new_html,
        flags=re.IGNORECASE
    )
    return new_html, count

def process_file(p: Path, apply: bool) -> str:
    original = p.read_text(encoding='utf-8', errors='ignore')
    html = original
    html, added_css = add_css_link(html)
    html, img_changes = normalize_img_tags(html)
    changed = (html != original)
    report = f"{p}: css_link={'added' if added_css else 'ok'}, imgs_changed={img_changes}"
    if apply and changed:
        p.write_text(html, encoding='utf-8')
    return report

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', required=True)
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()
    root = Path(args.root)
    html_files = list(root.glob("*.html"))
    # also include top-level subpages if present
    for sub in ["", "site", "pages"]:
        d = root / sub
        if d.is_dir():
            html_files.extend(d.glob("*.html"))

    seen = set()
    out_lines = ["# Site Unifier report", f"root: {root}", f"mode: {'apply' if args.apply else 'dry-run'}", ""]
    for p in sorted(set(html_files)):
        try:
            rep = process_file(p, apply=args.apply)
        except Exception as e:
            rep = f"{p}: ERROR {e}"
        out_lines.append(rep)

    print("\\n".join(out_lines))

if __name__ == "__main__":
    main()
