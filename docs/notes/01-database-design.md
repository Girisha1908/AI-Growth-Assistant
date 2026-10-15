# Phase 1: Database design

**Status:** done. Code: `models.py`, `migrate.py`.

## Idea
Keep chat data and vectors in **one** Postgres (pgvector). Fewer moving parts than a separate vector database.

```
episodes 1──* chunks(embedding)      sessions 1──* messages(sources, artifact)
profile (1 row)                      notes
```

## Key rules
* **Key rule:** a chunk must always lead back to a source (chunk → episode → YouTube + second).
* Store *how* a chunk was embedded (`embed_model`). Vectors from different models cannot be compared.
* `tsv` (generated column) + GIN index = fast keyword search; HNSW index = fast vector search.
* `create_all` never alters old tables, so `migrate.py` adds columns only if missing.

## Lesson from the build
`ALTER TABLE … ADD COLUMN IF NOT EXISTS` still takes an exclusive lock. A test hung because of it. Fix: check the catalog first, then run DDL only if needed, with a `lock_timeout`.

## Interview questions
1. Why pgvector over Pinecone/Chroma? 2. What is an HNSW index (approximate nearest neighbours, trades a little recall for speed)? 3. How do you evolve a schema without losing data?
