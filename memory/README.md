## How agents access this memory

- Queries follow the schema defined in `ops/knowledge_schema.json`.
- Agents should:
  1. Read `memory/index.json` to discover documents.
  2. Filter by `tags`, `source`, or `type`.
  3. Optionally load full content from `memory/documents/...`.
- Results returned to GEORGE must include:
  - `document_id`
  - `title`
  - `score` (0–1 relevance)
  - `path`
  - optional: `source`, `tags`, `summary`
