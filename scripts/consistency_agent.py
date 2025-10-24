#!/usr/bin/env python3
"""
consistency_agent.py
- Checks style & structure conventions across the site.
- Validates: filenames, alt/text attributes, broken links (local), CSS token usage, heading order.
- Exits non-zero in --strict mode if violations > 0.
"""

import argparse, json, re, sys, os
from pathlib import Path
from html.parser import HTMLParser

TOKENS_PATTERN = re.compile(r"var\(--(color|space|radius|font)-[a-z0-9\-]+\)")
VALID_NAME = re.compile(r"^[a-z0-9\-]+\.(html|css|js|md)$")
H_TAG = re.compile(r"<h([1-6])[^>]*>", re.I)

class LinkAltParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.issues = []
        self.links = []
        self.heading_levels = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "img" and not attrs.get("alt"):
            self.issues.append(("missing_alt", f"img without alt @ line?"))
        if tag == "a":
            href = attrs.get("href")
            if href:
                self.links.append(href)

    def feed_with_headings(self, html):
        # heading order check
        for m in H_TAG.finditer(html):
            self.heading_levels.append(int(m.group(1)))
        self.feed(html)

def scan_repo(root: Path):
    issues = []
    local_paths = {str(p.relative_to(root)).replace("\\", "/") for p in root.rglob("*") if p.is_file()}
    html_files = [p for p in root.rglob("*.html")]

    # File naming
    for p in root.rglob("*.*"):
        rel = str(p.relative_to(root)).replace("\\", "/")
        if "/.git/" in rel or "/venv/" in rel:
            continue
        if not VALID_NAME.search(p.name):
            issues.append(("bad_filename", rel))

    # CSS token usage
    for css in root.rglob("*.css"):
        text = css.read_text(encoding="utf-8", errors="ignore")
        # encourage CSS custom properties
        if "var(--" not in text:
            issues.append(("no_css_tokens", str(css.relative_to(root))))

    # HTML checks
    for f in html_files:
        html = f.read_text(encoding="utf-8", errors="ignore")
        parser = LinkAltParser()
        parser.feed_with_headings(html)
        for iss in parser.issues:
            issues.append((iss[0], f"{f} -> {iss[1]}"))

        # heading order (no jumps > 1 downwards)
        last = None
        for lvl in parser.heading_levels:
            if last is not None and lvl - last > 1:
                issues.append(("heading_jump", f"{f}: h{last} -> h{lvl}"))
            last = lvl

        # local link existence (basic)
        for href in parser.links:
            if href.startswith(("http://", "https://", "mailto:", "#")):
                continue
            candidate = (f.parent / href).resolve()
            if not candidate.exists():
                issues.append(("broken_local_link", f"{f} -> {href}"))

    return issues

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--path", default=".", help="project root")
    ap.add_argument("--out", default="ops/consistency_report.json")
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args()

    root = Path(args.path).resolve()
    issues = scan_repo(root)

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump({"issues": issues, "count": len(issues)}, fh, indent=2)

    print(f"[consistency_agent] found {len(issues)} issue(s). report -> {args.out}")
    if args.strict and issues:
        sys.exit(1)

if __name__ == "__main__":
    main()
