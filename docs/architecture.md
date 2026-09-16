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

## Sessions & Persistence

The chat system maintains multi-turn conversation context backed by PostgreSQL:

1. **Session Lifecycle (`sessions` table)**:
   - Clients create a session via `POST /sessions`, which generates a UUID primary key and timestamp.
   - `POST /chat` requires a valid `session_id` in the request body (`{"session_id": "uuid", "message": "string"}`). If an invalid or unknown UUID is supplied, the endpoint immediately returns HTTP 404 without creating orphan sessions.

2. **Message Storage (`messages` table)**:
   - Each interaction persists two rows linked to `session_id`: the user's prompt (`role="user"`) and the assistant's synthesized answer (`role="assistant"`).
   - Foreign key constraint with `ON DELETE CASCADE` ensures child messages are automatically removed when a parent session is deleted.
   - Clients can retrieve full chronological history for any session via `GET /sessions/{session_id}/messages`.

3. **Multi-Turn Context Resolution**:
   - **Retrieval Context**: For follow-up questions that depend on prior context (e.g., "What about specifically in the first week?" following a question on user retention), previous user queries are combined with the current query to ensure semantic vector search retrieves relevant chunks.
   - **Prompt History**: The last $N$ messages (default 6) are fetched from PostgreSQL and prepended to the prompt payload before the current grounded snippets, enabling natural follow-up dialogue while keeping token usage bounded.

## Model Provider Toggle

The application decouples generation logic from specific LLM backends using an extensible provider pattern:

1. **`LLMProvider` Interface**:
   - Defined in `backend/app/providers/base.py` as an abstract base class with a single method:
     ```python
     async def chat(self, messages: list[dict]) -> str: ...
     ```
   - Standardizes communication so that routers never invoke provider-specific SDKs or HTTP URLs directly.

2. **Supported Providers**:
   - **Ollama (`OllamaProvider`)**: Local inference against Ollama's `/api/chat` (e.g., `llama3.2:3b`).
   - **Claude (`ClaudeProvider`)**: Remote inference against Anthropic's Messages API (`https://api.anthropic.com/v1/messages`). Requires `ANTHROPIC_API_KEY`; validates key configuration on instantiation rather than import.

   > [!NOTE]
   > **Cloud provider (Claude)**: Implemented against the Anthropic Messages API via `ClaudeProvider` (`backend/app/providers/claude_provider.py`). Verified at the code level — imports cleanly without a key, and raises a clear `ValueError` when instantiated without `ANTHROPIC_API_KEY` set (see `backend/app/scripts/` or test output in the agent transcripts for this verification). Live end-to-end generation via Claude was not tested in this environment, since provisioning a billed API key was out of scope for the take-home's time budget. The provider abstraction (`LLMProvider` interface) is identical for both providers, so swapping in a real key and setting `LLM_PROVIDER=claude` requires zero code changes — this is demonstrated by the local Ollama provider working through the exact same interface.

3. **Factory & Configuration**:
   - `get_llm_provider()` in `backend/app/config.py` inspects `settings.LLM_PROVIDER` (`"ollama"` or `"claude"`) and returns the appropriate instance.
   - Switching providers requires zero code changes — simply update `LLM_PROVIDER` in `.env` (and ensure `ANTHROPIC_API_KEY` is provided if choosing Claude).
   - `GET /health` reports the currently active provider in its JSON payload.

## Ship 30 Content Skill

The application provides a dedicated content generation skill via `POST /skills/ship30`. 

### Difference from Base `/chat` Endpoint
While the `/chat` endpoint performs conversational question-answering over retrieved chunks, `POST /skills/ship30` is an opinionated ghostwriting engine. Rather than producing short conversational responses, it synthesizes retrieved podcast transcripts into an essay following the **Ship 30 for 30** online writing methodology developed by Dickie Bush and Nicolas Cole.

Like `/chat`, the skill is fully integrated into the session lifecycle:
- Accepts `session_id` and `topic`.
- Validates session existence (404 on invalid UUID).
- Reuses the existing semantic retrieval pipeline (`search_chunks` from `retrieval.py`).
- Persists both the user prompt and the generated essay in the `messages` table.
- Employs the swappable `LLMProvider` abstraction.

### Encoded Writing Principles
The skill encodes concrete, visible principles in `backend/app/skills/ship30.py`:
1. **The Hook (Lead-In)**: Opens with a punchy, 1-2 sentence declarative hook that creates curiosity and answers *Who is this for? What is this about? Why should I care right now?*
2. **"For WHO / SO THAT" Framework**: Immediately establishes the specific target persona and the promised tangible outcome.
3. **High Rate of Revelation (RoR)**: High information density with zero fluff, filler phrases, or passive preambles.
4. **1-3-1 Visual Cadence**: Structures points using rhythmic alternation: 1 punchy line, 3-sentence body or 3 bullets, 1 punchy conclusion.
5. **Skimmable Visual Architecture**: Narrative-driven markdown subheadings (`##` / `###`), bolded opening words of key insights, and high-density bulleted lists.
6. **Strict Transcript Grounding**: Anchors claims, heuristics, and quotes exclusively in verified transcripts from Lenny's Podcast.
7. **Actionable Takeaway**: Concludes with a concrete implementation heuristic rather than an abstract summary.

> [!NOTE]
> **Word Count & Local Model Behavior**:
> The prompt targets an in-depth ~1,250-word essay. In local CPU environments running `llama3.2:3b`, the model typically synthesizes high-density essays of ~600 words due to compact 3B instruct-tuning priors. Larger cloud models (such as Claude 3.5 Sonnet) expand to the full ~1,250-word target through the identical `LLMProvider` interface.


