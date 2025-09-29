#!/usr/bin/env python3
"""
Image Consistency Agent
Ensures consistent <img> markup across HTML files.
"""
import os
import re
import argparse
from pathlib import Path
from bs4 import BeautifulSoup

def process_html(file_path, apply=False, set_dimensions=False):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    soup = BeautifulSoup(content, "html.parser")
    changed = False

    imgs = soup.find_all("img")
    for i, img in enumerate(imgs):
        # Ensure class
        existing_classes = img.get("class", [])
        if "responsive-img" not in existing_classes:
            existing_classes.append("responsive-img")
            img["class"] = existing_classes
            changed = True

        # Lazy loading (first img eager)
        if i == 0:
            img["loading"] = "eager"
        else:
            img["loading"] = "lazy"
        img["decoding"] = "async"
        changed = True

        # Remove inline width/height styles
        if img.has_attr("style"):
            styles = img["style"].split(";")
            styles = [s for s in styles if not any(k in s for k in ["width", "height"])]
            img["style"] = ";".join(styles).strip()
            changed = True

    if changed and apply:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(str(soup))
    return changed

def main():
    parser = argparse.ArgumentParser(description="Unify <img> tags across HTML files.")
    parser.add_argument("--root", type=str, required=True, help="Root directory to scan")
    parser.add_argument("--apply", action="store_true", help="Apply fixes in place")
    parser.add_argument("--dry-run", action="store_true", help="Preview only")
    parser.add_argument("--set-dimensions", action="store_true", help="Set intrinsic width/height (needs Pillow)")
    args = parser.parse_args()

    root = Path(args.root)
    html_files = list(root.rglob("*.html"))
    log_lines = []

    for html_file in html_files:
        changed = process_html(html_file, apply=args.apply, set_dimensions=args.set_dimensions)
        if changed:
            log_lines.append(f"Updated {html_file}")
        else:
            log_lines.append(f"No changes {html_file}")

    log_path = Path("logs") / f"image-consistency.log"
    with open(log_path, "w", encoding="utf-8") as f:
        f.write("\n".join(log_lines))

    print(f"Processed {len(html_files)} HTML files. Log written to {log_path}")

if __name__ == "__main__":
    main()
