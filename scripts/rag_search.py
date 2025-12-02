#!/usr/bin/env python3
"""
Simple RAG memory search helper for virtauto.de

- liest memory/index.json
- prüft, ob es zu jedem Eintrag ein Embedding in memory/embeddings/ gibt
- macht eine sehr einfache Textsuche über Titel, Tags und Summary
"""

import json
import pathlib
import sys
import textwrap

ROOT = pathlib.Path(__file__).resolve().parent.parent
INDEX_PATH = ROOT / "memory" / "index.json"
EMBED_DIR = ROOT / "memory" / "embeddings"


def load_index():
    with INDEX_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def search_index(query: str):
    data = load_index()
    q = query.lower()
    results = []

    for doc in data.get("documents", []):
        haystack = " ".join([
            doc.get("title", ""),
            doc.get("summary", ""),
            " ".join(doc.get("tags", [])),
        ]).lower()

        if q in haystack:
            results.append(doc)

    return results


def embedding_exists(doc_id: str) -> bool:
    # Embedding-Dateien heißen z.B. doc-001.json, doc-002.json ...
    emb_file = EMBED_DIR / f"{doc_id}.json"
    return emb_file.exists()


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/rag_search.py <query>")
        sys.exit(1)

    query = " ".join(sys.argv[1:])
    print(f"🔎 Searching virtauto memory for: {query!r}\n")

    results = search_index(query)

    if not results:
        print("No matches in memory/index.json")
        return

    for i, doc in enumerate(results, start=1):
        doc_id = doc.get("id")
        print(f"[{i}] {doc.get('title', '(no title)')}")
        print(f"    id:   {doc_id}")
        print(f"    path: {doc.get('path')}")
        print("    tags:", ", ".join(doc.get("tags", [])))

        summary = (doc.get("summary") or "").strip()
        if summary:
            print("    summary:",
                  textwrap.shorten(summary, width=120, placeholder="…"))

        has_emb = embedding_exists(doc_id)
        print(f"    embedding: {'YES' if has_emb else 'NO (missing)'}")
        print()


if __name__ == "__main__":
    main()
