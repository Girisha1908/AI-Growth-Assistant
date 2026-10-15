# CLAUDE.md: Lenny Growth Assistant

RAG chat app over Lenny's Podcast transcripts (FDE take-home). FastAPI + Postgres/pgvector + React (Vite, Tailwind) + Ollama. Spec: `docs/prd.md`. Design: `docs/architecture.md`, `docs/design.md`. Manual UI plan: `docs/testing.md`.

## Environment

* Windows, PowerShell. Use `curl.exe` (not `curl`), `Copy-Item` (not `cp`).
* Docker Desktop runs api, db and frontend. Ollama runs on the HOST at `http://localhost:11434`; containers reach it at `http://host.docker.internal:11434`.
* If `ollama` is not on PATH, use `& "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe"`.
* Needed models: `nomic-embed-text`, `llama3.2:3b`.

## Rules (important)

1. Ask the user before installing anything, pulling models, deleting Docker volumes, or running anything with admin rights. Give the exact command and say where to run it (host or container).
2. Never push. Commit per phase with conventional messages (`feat:`, `fix:`, `docs:`); the user reviews the diff and pushes.
3. Never commit `.env`, `transcripts/source/`, `transcripts/ingest.log` or `eval/last_run.md`.
4. After each phase, save a short log to `transcripts/claude-code-<phase>.md`. Include failed attempts and fixes; redact secrets.
5. Don't change retrieval thresholds or chunking without re-running `python eval/run_eval.py` and reporting before/after.
6. Long jobs (full ingestion) run detached; never block the session on them.

## Commands

```powershell
docker compose up -d --build
curl.exe http://localhost:8000/health
curl.exe http://localhost:8000/health/chunks
docker compose exec -d api sh -c "python -m app.scripts.ingest > /app/transcripts/ingest.log 2>&1"
Get-Content transcripts\ingest.log -Tail 5
docker compose exec api sh -c "pip install -q -r requirements-dev.txt && pytest"
docker compose exec frontend npm test
python eval/run_eval.py
docker compose logs api --tail 50
```

## Layout

* `backend/app/`: `routers/` (HTTP), `agent/` (router, prompts, skills), `providers/` (Ollama, Claude, Claude Agent SDK), `retrieval.py` (hybrid + gate), `embeddings.py`, `ingestion/`, `scripts/ingest.py`, `migrate.py`
* `backend/tests/`: pytest; needs Postgres, uses fake model and fake embeddings
* `frontend/src/`: `components/`, `hooks/`, `lib/` (`sandbox.js` = artifact security; do not weaken)
* `eval/`: questions and harness for PRD metrics M1–M3

## Status

* Verified in a sandbox: 76 backend tests (real Postgres), 14 frontend tests, frontend build, pipeline with a stub model.
* Never verified: Docker build on this machine, real Ollama answers, ingestion speed, UI in a browser, Claude providers (no API key).
* Older DB may hold 100 episodes of legacy chunks; ingestion upgrades them in place.

## Definition of done

1. `docker compose up -d --build` succeeds; `/health` reports `ok`.
2. All 303 episodes ingested: `/health/chunks` shows `episodes: 303`, `legacy_chunks_without_metadata: 0`.
3. Backend and frontend tests pass inside the containers.
4. `eval/run_eval.py` meets M1 ≥ 90%, M2 = 100%, M3 = 100%, or the gap is explained in `docs/prd.md`.
5. Every manual check in `docs/testing.md` passes (the user does the browser steps; ask them).
6. README steps work from a fresh clone.
