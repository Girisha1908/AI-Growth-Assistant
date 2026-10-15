# Architecture

## 1. System overview

```
┌────────────┐  HTTP/JSON   ┌───────────────────────────── FastAPI ─────────────────────────────┐
│ React UI   │─────────────▶│ routers ─▶ agent runner ─▶ router (intent) ─▶ skill ─▶ LLMProvider │──▶ Ollama (local, default)
│ (Vite,     │◀─────────────│     │           │                                                │──▶ Claude API / Agent SDK (opt-in)
│  Tailwind) │  answer +    │     │           └─▶ retrieval (hybrid) ─▶ embeddings client ─────┼──▶ Ollama /api/embed
└────────────┘  sources +   │     ▼                                                            │
   sandboxed    artifact    │  PostgreSQL 16 + pgvector  (episodes, chunks, sessions, messages, │
   iframe                   │                             profile, notes)                       │
                            └──────────────────────────────────────────────────────────────────┘
```

| Boundary | Responsibility | Never does |
|---|---|---|
| `routers/` | HTTP contracts, validation, persistence of turns | Prompting, retrieval SQL |
| `agent/` | Intent routing, prompts, skills, orchestration | Talk to a specific model vendor |
| `providers/` | One class per model backend behind `LLMProvider` | Retrieval, routing |
| `retrieval.py`, `embeddings.py` | Search and vectors (same embedding model for docs and queries) | Generate answers |
| `ingestion/`, `scripts/ingest.py` | Parse, chunk, embed, store transcripts | Serve requests |
| `frontend/` | Rendering, sandboxing untrusted HTML | Business rules |

## 2. Database schema

| Table | Key columns | Notes |
|---|---|---|
| `episodes` | `id`, `slug` (unique), `guest`, `title`, `youtube_url`, `video_id`, `publish_date`, `duration_seconds`, `keywords` (json), `chunk_count` | One row per transcript header |
| `chunks` | `id`, `episode_id` → episodes, `source_file`, `chunk_index`, `content`, `start_seconds`, `embedding vector(768)`, `embed_model`, `tsv tsvector` (generated) | Unique `(source_file, chunk_index)`. HNSW index on `embedding`, GIN on `tsv` |
| `sessions` | `id`, `created_at`, `metadata` (json: user agent, client info) | One per chat. Contexts never mix |
| `messages` | `id`, `session_id` → sessions (cascade), `role`, `content`, `mode`, `sources` (json), `artifact` (json), `meta` (json), `created_at` | Sources and artifact are stored with the assistant turn |
| `profile` | `id` (always 1), `display_name`, `goal`, `background`, `known_concepts`, `updated_at` | Single-user learner profile |
| `notes` | `id`, `title`, `kind` (note/markdown/html/answer), `content`, `sources`, `created_at` | The personal library |

`app/migrate.py` upgrades an older database in place (adds columns/indexes only if missing; `lock_timeout` guards it). Alembic is the production answer and is listed under limits.

## 3. API

All errors: `{"error": {"code", "message", "hint"}}`. Every response carries `x-request-id`.

| Method & path | Purpose |
|---|---|
| `POST /sessions` · `GET /sessions` · `GET /sessions/{id}/messages` · `DELETE /sessions/{id}` | Chats and history |
| `POST /chat` | `{session_id, message, mode?, provider?, personalize?}` → `{answer, sources[], artifact?, meta}` |
| `POST /skills/ship30` | Dedicated Ship 30 for 30 endpoint (same agent, `mode=ship30`) |
| `POST /search` | Retrieval only (no model). Used by the eval harness |
| `GET /episodes` · `GET /episodes/{id}` | Browse the knowledge base |
| `GET/PUT /profile` · `GET/POST/DELETE /notes` | Personalisation and library |
| `GET /health` · `GET /health/chunks` · `GET /config` | Real DB/provider checks, corpus stats, public settings |
| `POST /client-events` | Frontend error reports (e.g. artifact render failures) |

Modes: `auto` (default), `ask`, `explain`, `quiz`, `ship30`, `artifact`, `prd`.

## 4. Ingestion (load → chunk → index → refresh → trace)

1. **Load**: `python -m app.scripts.ingest` clones `ChatPRD/lennys-podcast-transcripts` into `transcripts/source/` (gitignored; we don't vendor someone else's repo).
2. **Parse**: YAML header → `episodes`; body split into paragraphs; the latest `(HH:MM:SS)` timestamp is carried forward.
3. **Chunk**: paragraphs packed to about 500 words with 50 words of overlap; speaker labels kept; each chunk stores `start_seconds`.
4. **Embed**: batches of 16 to Ollama `nomic-embed-text` (768 dims). Prefixes optional (`EMBED_USE_PREFIXES`, off by default because the threshold was calibrated without them).
5. **Index**: per-episode atomic transaction (delete old chunks, insert new). Generated `tsv` and HNSW indexes make search fast.
6. **Refresh**: re-run the script. Episodes already embedded with the current setup are skipped; `--force` re-embeds. `embed_model` per chunk prevents silently mixing vectors from different setups.
7. **Trace**: chunk → episode → guest, title, date, YouTube URL at the exact second.

## 5. Retrieval and grounding

```
question ─┬─ embed ─▶ top-20 by cosine distance (pgvector) ────────────┐
          └─ keywords (stop-words removed) ▶ top-20 full-text (tsvector)┴▶ RRF fusion
GATE: best vector distance > RELEVANCE_MAX_DISTANCE (0.45)?  ──yes──▶ refuse, model NOT called
else: keep chunks within threshold (keyword-only hits get +0.10 margin), max 2 per episode, top 4
```

* Follow-ups under 9 words are searched together with the previous user question.
* The prompt numbers the excerpts `[1]…[n]`; the UI maps `[n]` to citation cards. **The sources list comes from database rows, never from model text.**
* If the model itself replies with the refusal sentence, sources are dropped.

## 6. Agent routing and skills

`agent/router.py` chooses a skill from an explicit `mode` or, in `auto`, by regex rules (no extra model call; deterministic and testable). Each skill is one module with `run(ctx)`.

| Skill | Output |
|---|---|
| ask | Grounded answer with `[n]` citations |
| explain | Plain-language answer with an analogy tuned to the learner profile |
| quiz | Markdown quiz with collapsible answers |
| ship30 | Markdown essay. Principles are encoded as constants in `skills/ship30.py`. Strategy `sectioned` = outline + one call per section (hook, 4 sections, takeaway) so small models reach ~1,250 words; falls back to `single` if the outline cannot be parsed |
| artifact | Markdown document or complete HTML page |
| prd | PRD in Markdown with an evidence section |

To add a skill: new module with `NAME` and `run`, register it in `skills/__init__.py`, add a rule in `router.py`.

## 7. Model toggle and fallback

`config.get_llm_provider()` returns `OllamaProvider`, `ClaudeProvider` (HTTP) or `ClaudeAgentProvider` (Claude Agent SDK, tools disabled) from `LLM_PROVIDER`, or from the per-request `provider` override in the UI. Only the `LLMProvider` interface is visible to the rest of the code.

* **The brief names the Claude Agent SDK; the demo must run on Ollama.** The SDK drives only Claude, so routing and skills live in our provider-agnostic `agent/` layer and the SDK is one provider. It is written against SDK 0.2.x and **has not been run against the live API**.
* **Fallback policy:** none automatic. If Ollama is down the API returns `provider_unavailable` (503) with a hint; if a key is missing, `provider_not_configured` (400). The user switches providers explicitly, because silently sending data to a paid service would be a surprise.

## 8. Artifact security

Generated HTML is untrusted. Three layers (`frontend/src/lib/sandbox.js`, tested):

1. `<iframe sandbox>` with **no** `allow-same-origin`: opaque origin, so no access to our storage, cookies, API identity or parent DOM. No popups, forms, downloads, top navigation. Scripts off by default; an opt-in checkbox enables them, still isolated.
2. Injected **CSP** `default-src 'none'`: no network access of any kind, so nothing can be exfiltrated.
3. **Sanitising**: removes scripts (unless opted in), meta refresh, base, iframes, forms, event handlers; neutralises links; keeps `data:` images.

Markdown is rendered with `rehype-sanitize` (GitHub allow-list) after `rehype-raw`. HTML artifacts cannot be printed from the parent (cross-origin frame), so they offer download instead.

## 9. Observability and resilience

* JSON logs, one object per line, with `request_id`. Events: `request`, `route`, `retrieval` (reason, best distance, hits, ms), `llm_call` (provider, model, ms, ok), `artifact_generated`, `client_event`, `schema_ready`, `app_error`. Try: `docker compose logs api | jq`.
* Failures handled without a 500: Ollama down (chat and embeddings), missing key, timeout (504), empty retrieval (refusal), bad model output (502), database down (503, API still starts and `/health` shows `degraded`).
* A failed request persists nothing, so retry never duplicates a turn.

## 10. Deployment topology

`docker compose up --build` starts `db` (pgvector/pgvector:pg16, volume), `api` (FastAPI on :8000, waits for DB health) and `frontend` (Vite on :5173). Ollama runs on the host and is reached at `host.docker.internal:11434`. No live cloud deployment is required by the brief.

## 11. Known limits

* Ingestion speed and answer quality depend on the evaluator's hardware.
* Hybrid keyword search is OR-based with no IDF weighting; it mainly re-ranks vector candidates.
* No Alembic, auth, streaming or reranker.
* Claude and Agent SDK paths are code-verified only.
