#!/usr/bin/env python
"""
Simple RAG search helper for virtauto.de

Loads all embeddings from memory/embeddings/*.json and returns
the most relevant documents for a given query string.

V1.0: purely CLI-based. Later, GEORGE or andere Agents können
dieses Script als Tool aufrufen.
"""

import json
import math
import hashlib
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
EMB_DIR = REPO_ROOT / "memory" / "embeddings"


def deterministic_embedding(text: str, dim: int = 64):
    """Muss zur Funktion in rag_embed.py kompatibel sein."""
    if not text:
        text = " "

    h = hashlib.sha256(text.encode("utf-8")).digest()
    data = (h * ((dim // len(h)) + 1))[:dim]
    return [((b / 127.5) - 1.0) for b in data]


def cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def load_embeddings():
    vectors = []
    for f in sorted(EMB_DIR.glob("*.json")):
        with f.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        vectors.append(
            {
                "id": data.get("id"),
                "source_path": data.get("source_path"),
                "title": data.get("meta", {}).get("title"),
                "tags": data.get("meta", {}).get("tags", []),
                "vector": data.get("vector", []),
            }
        )
    return vectors


def search(query: str, top_k: int = 3):
    q_vec = deterministic_embedding(query)
    docs = load_embeddings()

    scored = []
    for d in docs:
        score = cosine(q_vec, d["vector"])
        scored.append((score, d))

    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[:top_k]


def main():
    if len(sys.argv) < 2:
        print("Usage: python tools/rag_search.py \"your question here\"")
        sys.exit(1)

    query = " ".join(sys.argv[1:])
    print(f"\n🔎 Query: {query}\n")

    results = search(query, top_k=5)
    for rank, (score, doc) in enumerate(results, start=1):
        print(f"#{rank}  score={score:.3f}")
        print(f"    id:    {doc['id']}")
        print(f"    title: {doc['title']}")
        print(f"    path:  {doc['source_path']}")
        print(f"    tags:  {', '.join(doc['tags'])}")
        print()

if __name__ == "__main__":
    main()
