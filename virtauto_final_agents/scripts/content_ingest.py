#!/usr/bin/env python3
import argparse, os, feedparser, re, pathlib, datetime as dt

FRONTMATTER_TMPL = """---
title: "{title}"
date: "{date}"
tags: ["virtauto","agents"]
description: "{desc}"
canonical: "{link}"
draft: true
---

{summary}

"""

def slugify(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+","-",s).strip("-")
    return s[:80]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--feed", required=True)
    ap.add_argument("--out", default="content/drafts")
    args = ap.parse_args()

    feed = feedparser.parse(args.feed)
    outdir = pathlib.Path(args.out); outdir.mkdir(parents=True, exist_ok=True)
    today = dt.date.today().isoformat()

    for e in feed.entries[:5]:
        title = e.get("title","(untitled)")
        link  = e.get("link","")
        summary = e.get("summary","").strip()
        desc = (summary[:140]+"…") if len(summary)>140 else summary
        slug = f"{today}-{slugify(title)}"
        path = outdir / f"{slug}.md"
        if path.exists(): 
            continue
        path.write_text(FRONTMATTER_TMPL.format(title=title.replace('"','\"'),
                                                date=today, desc=desc.replace('\n',' '), link=link,
                                                summary=summary), encoding="utf-8")
        print("Wrote", path)

if __name__ == "__main__":
    main()
