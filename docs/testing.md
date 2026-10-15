# Testing

## Automated

| Suite | Command | Covers |
|---|---|---|
| Backend (76 tests, real Postgres + pgvector) | `docker compose exec api sh -c "pip install -q -r requirements-dev.txt && pytest"` | Parsing and chunking, ingestion (idempotent, atomic, resumable), legacy DB upgrade, hybrid search and gate, routing, API contracts, sessions and persistence across restart, provider failures (503/504/502/400), DB down, validation, skills, artifacts, profile, notes, health |
| Frontend (14 tests) | `docker compose exec frontend npm test` | HTML sandbox (CSP, stripped scripts, neutralised links), Markdown sanitising, citation linking, API error parsing |
| Evaluation set | `python eval/run_eval.py` (retrieval only, seconds) or `--full` | M1 grounded rate, M2 refusal rate, M3 citation validity (and M4 latency with `--full`) |

Tests use a separate `lenny_test` database, a scripted fake model and hash-based fake embeddings, so no Ollama or API key is needed. They do **not** measure real answer quality: use the eval set after ingestion.

## Manual UI test plan (about 10 minutes)

| # | Steps | Expected |
|---|---|---|
| 1 | Open http://localhost:5173 | Greeting and composer; sidebar status dot is green (hover shows provider and model) |
| 2 | Toggle theme | Light and dark both readable; choice persists on reload |
| 3 | Ask "How should product teams improve user retention?" | Pulsing dots, then answer with `[n]` chips and source pills |
| 4 | Click a `[n]` chip, then "Open on YouTube at …" | Pill expands with the excerpt; YouTube opens at the timestamp |
| 5 | Ask "What is the capital of France?" | One line: not covered by the transcripts; no sources |
| 6 | Ask "what about the first week?" | Answer uses the previous topic |
| 7 | New chat; ask the same short follow-up | Refusal (no leaked context) |
| 8 | Mode menu → Ship 30 essay → "why retention beats acquisition" | Essay opens in the right panel |
| 9 | Mode menu → Document / HTML → "give me an HTML card for retention" | Renders in the sandbox; Code tab shows source; no console errors |
| 10 | In an HTML artifact containing a script, toggle "Allow scripts" | Still no network or navigation |
| 11 | Quiz mode | Answers are collapsed until clicked |
| 12 | Save an artifact; open Library; reopen; delete | Library works |
| 13 | Transcripts tab: search "chesky"; "Ask about this" | Filter works; composer prefilled |
| 14 | Profile: set goal and known concepts; Explain mode | Analogy references your background; the profile toggle turns this off |
| 15 | Stop Ollama; send a message | Error card with hint and Retry; no half message in history |
| 16 | Sidebar Recents | Previous chats listed, reopenable, deletable on hover |
| 17 | Narrow the window below 1024 px | Sidebar becomes a drawer; artifact a full-screen overlay |
| 18 | Keyboard only: Tab through composer, send with Enter | Visible focus everywhere |
