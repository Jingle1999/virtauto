#!/usr/bin/env python
"""
Simple RAG embedding builder for virtauto.de

Reads memory/index.json and all referenced documents under memory/documents/,
creates deterministic "embeddings" as numeric vectors and writes them to
memory/embeddings/<doc_id>.json.

This is V1.0: placeholder embeddings. Later you can replace the embedding
function with a real model call (OpenAI, etc.) without changing the workflow.
"""

import json
import hashlib
from pathlib import Path
from datetime import datetime

REPO_ROOT = Path(__file__).resolve().parents[1]
MEMORY_DIR = REPO_ROOT / "memory"
DOC_DIR = MEMORY_DIR / "documents"
EMB_DIR = MEMORY_DIR / "embeddings"
INDEX_FILE = MEMORY_DIR / "index.json"

EMB_DIR.mkdir(parents=True, exist_ok=True)


def load_index():
    with INDEX_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def deterministic_embedding(text: str, dim: int = 64):
    """
    Very simple deterministic pseudo-embedding:
    - take SHA256 hash of the text
    - expand bytes to a fixed-length numeric vector

    This is NOT semantic, but it gives us a stable numeric vector for now.
    """
    if not text:
        text = " "

    h = hashlib.sha256(text.encode("utf-8")).digest()
    # repeat hash bytes to reach desired dimension
    data = (h * ((dim // len(h)) + 1))[:dim]
    # map bytes 0..255 to -1.0..+1.0
    return [((b / 127.5) - 1.0) for b in data]


def build_embeddings():
    index = load_index()
    docs = index.get("documents", [])

    updated = 0
    for doc in docs:
        doc_id = doc.get("id")
        rel_path = doc.get("path")
        if not doc_id or not rel_path:
            continue

        doc_path = REPO_ROOT / rel_path
        if not doc_path.exists():
            print(f"[WARN] Document not found: {rel_path}")
            continue

        text = doc_path.read_text(encoding="utf-8", errors="ignore")
        emb = deterministic_embedding(text, dim=64)

        emb_payload = {
            "id": doc_id,
            "source_path": rel_path,
            "version": "1.0.0",
            "dim": len(emb),
            "created_at": datetime.utcnow().isoformat() + "Z",
            "meta": {
                "title": doc.get("title"),
                "tags": doc.get("tags", []),
            },
            "vector": emb,
        }

        out_file = EMB_DIR / f"{doc_id}.json"
        with out_file.open("w", encoding="utf-8") as f:
            json.dump(emb_payload, f, ensure_ascii=False, indent=2)

        updated += 1
        print(f"[OK] Updated embedding for {doc_id} -> {out_file}")

    print(f"[DONE] Embeddings updated for {updated} document(s).")


if __name__ == "__main__":
    build_embeddings()
