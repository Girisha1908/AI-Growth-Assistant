# Architecture

## Ingestion Pipeline

The ingestion pipeline is a one-off script (`python -m app.scripts.ingest`) that
loads Lenny's Podcast transcripts into a vector-searchable format:

1. **Source**: Transcripts are cloned from
   [ChatPRD/lennys-podcast-transcripts](https://github.com/ChatPRD/lennys-podcast-transcripts)
   into `transcripts/source/`. Each episode lives in `episodes/{guest-name}/transcript.md`
   with YAML frontmatter (guest, title, YouTube URL, publish date) and the full
   transcript body.

2. **Chunking**: Each transcript is split into ~500-token chunks with ~50-token
   overlap. The splitter is paragraph-aware — it breaks on `\n\n` boundaries and
   combines paragraphs until hitting the token target. This prevents mid-sentence
   cuts while keeping chunks small enough for embedding models.

3. **Embedding**: Each chunk is sent to a local Ollama instance running
   `nomic-embed-text`, which returns a 768-dimensional vector. The embedding call
   is fault-tolerant — if Ollama is down or a chunk fails, the error is logged and
   that chunk is skipped rather than crashing the pipeline.

4. **Storage**: Chunks are stored in the `chunks` table in PostgreSQL with the
   `pgvector` extension. Each row contains:
   - `source_file`: relative path (e.g. `episodes/brian-chesky/transcript.md`)
   - `chunk_index`: position within the file (0-indexed)
   - `content`: the actual text
   - `embedding`: 768-dim vector for similarity search

5. **Traceability**: Every chunk retains its `source_file` and `chunk_index`, so
   when a retrieval query finds a relevant chunk, the system can cite the exact
   episode and approximate position within the transcript.

6. **Idempotency**: Re-running the script deletes existing chunks for each source
   file before re-inserting. This avoids duplicates and ensures the latest chunking
   logic is reflected.

## Ingestion Scope & Subset Choice

For this phase, we ingested a representative subset of 100/303 episodes due to time constraints; architecture supports full ingestion via re-running the script with the cap removed:

```bash
# Ingest subset (e.g. 100 episodes)
docker compose exec api python -m app.scripts.ingest --limit 100

# Full catalog ingestion (all 303 episodes)
docker compose exec api python -m app.scripts.ingest
```

## Retrieval & Generation

The system provides grounded question answering over the ingested podcast transcripts via the `POST /chat` endpoint:

1. **Query Embedding**: When a user submits a question (`{"message": "..."}`), the query text is sent to Ollama's `/api/embed` endpoint using `nomic-embed-text`, generating a 768-dimensional query vector matching the stored transcript chunks.

2. **Similarity Search (`<=>` Cosine Distance)**:
   SQLAlchemy queries PostgreSQL with `pgvector`'s cosine distance operator (`Chunk.embedding.cosine_distance(query_vector)`), ordering by distance ascending to fetch the top-k (default `k=5`) most relevant transcript passages.

3. **Relevance Thresholding**:
   Cosine distance ranges from 0.0 (identical) to 2.0 (opposite). If the nearest chunk's distance exceeds `0.45` (equivalent to cosine similarity < 0.55), the query is determined to be outside the scope of the transcripts. The endpoint returns an honest refusal (`"I don't have enough information from the transcripts to answer that."`) with empty sources, bypassing the LLM call entirely.

4. **Prompt Construction**:
   If relevant chunks are found, a strict grounding prompt is constructed with the retrieved transcript passages labeled by source file and chunk index. The prompt instructs the model to answer *only* using the provided context and to refuse to answer if the context is insufficient.

5. **Generation & Citation**:
   The prompt is dispatched to Ollama's `/api/chat` endpoint (e.g., `llama3.1:8b`). The API returns a structured JSON response:
   ```json
   {
     "answer": "...",
     "sources": [
       {"source_file": "episodes/archie-abrams/transcript.md", "chunk_index": 22}
     ]
   }
   ```
   The citations returned reflect the actual files retrieved from PostgreSQL, preventing hallucinated citations.


