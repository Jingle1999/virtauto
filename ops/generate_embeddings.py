from openai import OpenAI
import json, glob
import numpy as np

client = OpenAI()
EMBEDDING_MODEL = "text-embedding-3-small"

def load_index():
    with open("memory/index.json", "r", encoding="utf-8") as f:
        return json.load(f)["documents"]

def load_embeddings():
    embs = {}
    for path in glob.glob("memory/embeddings/doc-*.json"):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        embs[data["document_id"]] = np.array(data["vector"], dtype="float32")
    return embs

DOCS = load_index()
EMBS = load_embeddings()

def embed_query(query: str):
    res = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=query
    )
    return np.array(res.data[0].embedding, dtype="float32")

def search_memory(query: str, top_k: int = 5):
    q_vec = embed_query(query)
    results = []

    for doc in DOCS:
        doc_id = doc["id"]
        if doc_id not in EMBS:
            continue

        d_vec = EMBS[doc_id]
        score = float(np.dot(q_vec, d_vec))  # Embeddings sind normiert → Skalarprodukt = Cosine

        results.append({
            "document_id": doc_id,
            "title": doc["title"],
            "score": max(0.0, min(1.0, (score + 1) / 2)),  # auf 0–1 skalieren, wenn du willst
            "path": doc["path"],
            "source": doc["source"],
            "tags": doc.get("tags", []),
            "summary": doc.get("summary", "")
        })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_k]
