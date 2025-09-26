#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Aufräumen aller <head>-Blöcke in .html-Dateien:
- Nur einen <head> behalten (mehrere werden zusammengeführt)
- styles.css, styles_unify.css, site.js in richtiger Reihenfolge sicherstellen
- Duplikate von <link>/<script> entfernen
Verwendung:
  Trockenlauf:  python tidy_html_heads.py --root . --dry-run
  Anwenden:     python tidy_html_heads.py --root . --apply
"""

import argparse
import pathlib
import re
import shutil
import sys

HEAD_RE = re.compile(r"(?is)<head\b[^>]*>(.*?)</head>")
TAG_RE  = re.compile(r"(?is)<(meta|title|link|script)\b(.*?)(?:/>|>(.*?)</\1>)")

# Primitive Attribut-Extraktion (ohne externe Abhängigkeiten)
ATTR_RE = re.compile(r'''(\w[\w:-]*)\s*=\s*("([^"]*)"|'([^']*)')''')

def attrs_to_dict(attr_chunk: str):
    out = {}
    for m in ATTR_RE.finditer(attr_chunk or ""):
        key = m.group(1).lower()
        val = m.group(3) if m.group(3) is not None else m.group(4) or ""
        out[key] = val
    return out

def dedupe_preserve_order(items, key):
    seen = set()
    out = []
    for x in items:
        k = key(x)
        if k in seen:
            continue
        seen.add(k)
        out.append(x)
    return out

def normalize_head(head_html: str):
    """
    Zerlegt einen <head>-Inhalt in Kategorien und baut ihn normiert wieder auf.
    """
    metas, titles, links, scripts, others = [], [], [], [], []

    for m in TAG_RE.finditer(head_html):
        tag = m.group(1).lower()
        attr_chunk = m.group(2) or ""
        inner = (m.group(3) or "").strip()
        attrs = attrs_to_dict(attr_chunk)

        if tag == "meta":
            metas.append((attr_chunk.strip(), attrs))
        elif tag == "title":
            titles.append(inner)
        elif tag == "link":
            href = attrs.get("href", "").strip()
            rel  = (attrs.get("rel","").strip().lower())
            links.append((href, rel, attr_chunk.strip()))
        elif tag == "script":
            src = attrs.get("src","").strip()
            scripts.append((src, attr_chunk.strip(), inner))
        else:
            others.append(m.group(0))  # falls was Exotisches auftaucht

    # 1) Meta: charset/viewport einmalig bevorzugen
    def meta_key(m):  # m = (attr_chunk, attrs)
        a = m[1]
        if "charset" in a:
            return ("meta","charset")
        n = a.get("name","").lower()
        return ("meta", n or a.get("http-equiv","").lower() or a.get("content","")[:40])
    metas = dedupe_preserve_order(metas, meta_key)

    # 2) Title: erster Title gewinnt
    title_html = f"<title>{titles[0]}</title>" if titles else ""

    # 3) Links: Duplikate anhand href entfernen
    links = [l for l in links if l[0]]  # nur Links mit href
    links = dedupe_preserve_order(links, key=lambda l: ("link", l[0].lower()))

    # Sicherstellen: styles.css + styles_unify.css (in genau der Reihenfolge)
    WANT_LINKS = [
        ("assets/styles.css",        'rel="stylesheet"'),
        ("assets/styles_unify.css",  'rel="stylesheet"'),
    ]
    have = {href.lower() for (href,_,_) in links}
    for href, rel in WANT_LINKS:
        if href.lower() not in have:
            links.append((href, "stylesheet", f'rel="stylesheet" href="{href}"'))

    # Reorder: beide Pflicht-Links zuerst (in erwarteter Reihenfolge), danach die restlichen
    def sort_links(links):
        priority = { "assets/styles.css": 0, "assets/styles_unify.css": 1 }
        def lk(l):
            href = l[0].lower()
            return (priority.get(href, 100), href)
        return sorted(links, key=lk)
    links = sort_links(links)

    # 4) Scripts: Duplikate anhand src entfernen
    scripts = [s for s in scripts if s[0]]
    scripts = dedupe_preserve_order(scripts, key=lambda s: ("script", s[0].lower()))

    # Sicherstellen: assets/site.js (mit defer)
    have_scripts = {src.lower() for (src,_,_) in scripts}
    if "assets/site.js" not in have_scripts:
        scripts.append(("assets/site.js", 'src="assets/site.js" defer', ""))

    # Reorder: site.js ans Ende
    def sort_scripts(scripts):
        def sk(s):
            src = s[0].lower()
            return (0 if src != "assets/site.js" else 1, src)
        return sorted(scripts, key=sk)
    scripts = sort_scripts(scripts)

    # Neuaufbau des <head>-Inhalts
    parts = []
    # einige sinnvolle Standard-Metas beibehalten (sie sind schon in metas)
    for chunk, a in metas:
        parts.append(f"<meta {chunk}>" if not chunk.lower().startswith("charset") else f"<meta charset=\"{a['charset']}\">" if 'charset' in a else f"<meta {chunk}>")
    if title_html:
        parts.append(title_html)
    for href, rel, raw in links:
        # rohes Attribut-Fragment übernehmen, notfalls minimal bauen
        if 'href=' in raw:
            parts.append(f"<link {raw}>")
        else:
            parts.append(f"<link rel=\"stylesheet\" href=\"{href}\">")
    for src, raw, inner in scripts:
        # defer erzwingen, ohne andere Attribute zu zerstören
        if "defer" not in raw.lower():
            raw = raw.strip() + " defer"
        if 'src=' in raw:
            parts.append(f"<script {raw}></script>")
        else:
            parts.append(f"<script src=\"{src}\" defer></script>")

    # ggf. „others“ (unbekannte Head-Tags) hinten anhängen
    parts.extend(others)

    return "\n  ".join(parts)

def fix_file(path: pathlib.Path, apply=False):
    text = path.read_text(encoding="utf-8", errors="ignore")
    heads = HEAD_RE.findall(text)
    if not heads:
        return False, "no <head> found"

    # Zusammenführen: Inhalte aller Heads konkatenieren
    merged_head_inner = "\n".join(h.strip() for h in heads if h.strip())
    new_head_inner = normalize_head(merged_head_inner)

    # Ersetze ALLE <head>…</head> durch EINEN normierten Block
    new_text = HEAD_RE.sub("", text)  # alle entfernen
    # Erste Position für den neuen <head>: vor dem ersten <body> (falls vorhanden), sonst am Dokumentanfang
    body_pos = re.search(r"(?is)<body\b", new_text)
    if body_pos:
        insert_at = new_text[:body_pos.start()]
        remainder = new_text[body_pos.start():]
        new_text = f"{insert_at}<head>\n  {new_head_inner}\n</head>\n{remainder}"
    else:
        new_text = f"<head>\n  {new_head_inner}\n</head>\n{new_text}"

    changed = (new_text != text)
    if changed and apply:
        bak = path.with_suffix(path.suffix + ".bak")
        if not bak.exists():
            shutil.copyfile(path, bak)
        path.write_text(new_text, encoding="utf-8")
    return changed, "updated" if changed else "unchanged"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True, help="Wurzelverzeichnis (Repo)")
    ap.add_argument("--apply", action="store_true", help="Änderungen schreiben")
    ap.add_argument("--dry-run", action="store_true", help="Nur anzeigen, nichts schreiben")
    args = ap.parse_args()

    root = pathlib.Path(args.root).resolve()
    if not root.exists():
        print(f"Root nicht gefunden: {root}", file=sys.stderr)
        sys.exit(2)

    total = changed = 0
    for p in root.rglob("*.html"):
        # Backup-/Vendor-/Build-Verzeichnisse überspringen
        if any(part in {".git", "_site", "node_modules"} for part in p.parts):
            continue
        total += 1
        c, status = fix_file(p, apply=args.apply and not args.dry_run)
        if c:
            changed += 1
            print(f"[CHANGE] {p}")
        else:
            # optional kurz melden:
            # print(f"[OK]     {p} ({status})")
            pass

    mode = "APPLY" if args.apply and not args.dry_run else "DRY-RUN"
    print(f"\n[{mode}] geprüft: {total} Dateien, geändert: {changed}")

if __name__ == "__main__":
    main()
