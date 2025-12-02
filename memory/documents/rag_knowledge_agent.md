# virtauto.OS — RAG Knowledge Agent (Blueprint)

**Role**

The RAG Knowledge Agent is virtauto.OS’s primary interface to its long-term memory.
It answers questions, surfaces relevant context for other agents, and keeps track of
which parts of the knowledge base are most frequently used.

---

## 1. Inputs

- **Natural language queries**
  - From GEORGE (orchestration layer)
  - From other agents (Guardian, Monitoring, Content, future MAS agents)
- **System signals**
  - Active page / feature (`context` field)
  - Agent name that triggered the request
  - Optional tags (e.g. `["security", "governance"]`)

---

## 2. Core Functions

1. **Semantic Search**
   - Use `tools/rag_search.py` to query `memory/embeddings/*.json`
   - Return top-k documents with scores and basic metadata
   - Filter / boost by tags when requested (e.g. `security`, `cdt`, `mas`)

2. **Result Packaging**
   - Normalize result format:
     - `title`
     - `summary`
     - `source_path`
     - `score`
     - `tags`
   - Limit payload size for agents (short summaries instead of full docs)

3. **Attribution & Traceability**
   - Always include `source_path` so Guardian & humans can verify origin
   - Keep a lightweight log of queries and hits in future `memory/logs/`

---

## 3. Interfaces

**CLI Tool (V1.0)**  
- Entrypoint: `python tools/rag_search.py "your question here"`
- Output: top-k results printed to stdout for manual inspection

**Agent Tool (future V1.x)**
- GEORGE will call the Knowledge Agent via a tool definition, e.g.:

```yaml
tool_id: rag_knowledge_agent
description: "Semantic search over virtauto.OS knowledge base"
entrypoint: "python tools/rag_search.py"
