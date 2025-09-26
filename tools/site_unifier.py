#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Site Unifier: cleans <img> tags (remove width/height/style),
adds a consistent responsive class, and writes changes.
No lookbehinds are used (Python-friendly).
Usage:
  python tools/site_unifier.py --root . --dry-run
  python tools/site_unifier.py --root . --apply
"""

import argparse
import pathlib
import re
from typing import Tuple

IMG_TAG_RE = re.compile(r"<img([^>]*)>", flags=re.IGNORECASE)

# remove single attr (width/height/style) from an attribute string
REMOVE_ATTR_RE = re.compile(r'\s(?:width|height|style)\s*=\s*"[^"]*"', flags=re.IGNORECASE)

# find class="...". We’ll update its value; if not present we insert one.
CLASS_ATTR_RE = re.compile(r'\sclass\s*=\s*"([^"]*)"', flags=re.IGNORECASE)

def strip_img_size_attrs(attr_str: str) -> str:
    """Remove width/height/style attributes from the raw <img ...> attribute string."""
    # repeatedly remove any of the attributes until none is left
    before = None
    after = attr_str
    while before != after:
        before = after
        after = REMOVE_ATTR_RE.sub("", after)
    # normalize excessive whitespace
    after = re.sub(r"\s+", " ", after).strip()
    if after and not after.startswith(" "):
        after = " " + after
    return after

def ensure_class(attr_str: str, required_class: str = "img-fluid") -> str:
    """Ensure the <img> has the required CSS class (append if class= exists, else add)."""
    m = CLASS_ATTR_RE.search(attr_str)
    if m:
        classes = m.group(1).strip()
        tokens = [c for c in re.split(r"\s+", classes) if c]
        if required_class not in tokens:
            tokens.append(required_class)
        new_classes = " ".join(tokens)
        # replace the original class attribute value
        start, end = m.span(1)
        attr_str = attr_str[:start] + new_classes + attr_str[end:]
    else:
        # insert class attribute at the beginning (after the leading space if present)
        if attr_str.startswith(" "):
            attr_str = f' class="{required_class}"' + attr_str
        else:
            attr_str = f' class="{required_class}" ' + attr_str
    return attr_str

def transform_html(html: str) -> Tuple[str, int]:
    """Transform all <img> tags; return (new_html, num_changes)."""

    changes = 0

    def repl(m: re.Match) -> str:
        nonlocal changes
        attrs = m.group(1) or ""
        original_attrs = attrs

        # 1) remove width/height/style
        attrs = strip_img_size_attrs(attrs)
        # 2) ensure class= has img-fluid
        attrs = ensure_class(attrs, "img-fluid")

        if attrs != original_attrs:
            changes += 1
        return f"<img{attrs}>"

    new_html = IMG_TAG_RE.sub(repl, html)
    return new_html, changes

def process_file(p: pathlib.Path, apply: bool) -> Tuple[int, int]:
    """Return (#changes, #files_modified(0/1))."""
    text = p.read_text(encoding="utf-8", errors="ignore")
    new_text, num = transform_html(text)
    if num > 0 and apply:
        p.write_text(new_text, encoding="utf-8")
        return num, 1
    return num, 0

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True, help="repo/site root directory")
    ap.add_argument("--apply", action="store_true", help="write changes")
    ap.add_argument("--dry-run", action="store_true", help="preview only")
    args = ap.parse_args()

    root = pathlib.Path(args.root).resolve()
    html_files = list(root.glob("*.html")) + list(root.glob("*/*.html"))

    total_changes = 0
    modified_files = 0

    for fp in html_files:
        changes, wrote = process_file(fp, apply=args.apply and not args.dry_run)
        total_changes += changes
        modified_files += wrote

    mode = "apply" if args.apply and not args.dry_run else "dry-run"
    print(f"# Site Unifier\nroot: {root}\nmode: {mode}")
    print(f"files scanned: {len(html_files)}, imgs changed: {total_changes}, files modified: {modified_files}")

if __name__ == "__main__":
    main()
