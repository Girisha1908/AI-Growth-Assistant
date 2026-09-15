# 🚀 Lenny Growth Assistant

A RAG-powered AI chat assistant built on podcast transcripts. This repository contains a containerized FastAPI backend with PostgreSQL (pgvector), a transcript ingestion pipeline, and a minimal React health-check frontend.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) (v20+)
- [Docker Compose](https://docs.docker.com/compose/install/) (v2+)
- [Ollama](https://ollama.com/) running locally with the `nomic-embed-text` model pulled:
  ```bash
  ollama pull nomic-embed-text
  ```

## Quick Start

1. **Clone the repository**

   ```bash
   git clone <repo-url>
   cd lenny-growth-assistant
   ```

2. **Create your environment file**

   ```bash
   cp .env.example .env
   ```

   Edit `.env` if you need to change any defaults (the defaults work out of the box for local development).

3. **Start all services**

   ```bash
   docker compose up --build
   ```

4. **Verify everything is running**

   | Service  | URL                           |
   |----------|-------------------------------|
   | Frontend | http://localhost:5173          |
   | API      | http://localhost:8000          |
   | Health   | http://localhost:8000/health   |
   | Chunks   | http://localhost:8000/health/chunks |
   | API Docs | http://localhost:8000/docs     |

   The frontend should display live health data fetched from the FastAPI backend, which in turn performs a real database connectivity check against PostgreSQL.

## Ingesting Transcripts

The ingestion pipeline clones Lenny's Podcast transcripts, chunks them, embeds them with Ollama, and stores them in PostgreSQL with pgvector.

1. **Make sure Ollama is running** with `nomic-embed-text` pulled (see Prerequisites).

2. **Run the ingestion script** from inside the API container:

   ```bash
   docker compose exec api python -m app.scripts.ingest
   ```

   The script will:
   - Auto-clone the [transcript repo](https://github.com/ChatPRD/lennys-podcast-transcripts) on first run
   - Chunk ~269 episode transcripts into ~500-token pieces
   - Embed each chunk via Ollama's `nomic-embed-text` model (768 dimensions)
   - Store everything in the `chunks` table

   **Expected time**: ~10–20 minutes depending on hardware (embedding is the bottleneck). Progress is printed as it runs.

3. **Verify ingestion**:

   ```bash
   curl http://localhost:8000/health/chunks
   ```

   Should return a non-zero `total_chunks` count.

4. **Re-running** is safe — the script deletes existing chunks per source file before re-inserting (no duplicates).

## Architecture

```
┌──────────────┐     ┌──────────────┐     ┌─────────────────────┐
│   Frontend   │────▶│   FastAPI    │────▶│  PostgreSQL + pgvec │
│  (Vite/React)│     │   Backend    │     │      (pg16)         │
│  :5173       │     │  :8000       │     │  :5432              │
└──────────────┘     └──────────────┘     └─────────────────────┘
                            │
                      ┌─────▼─────┐
                      │  Ollama   │
                      │ (embed)   │
                      │ :11434    │
                      └───────────┘
```

See [docs/architecture.md](docs/architecture.md) for details on the ingestion pipeline.

## Project Structure

```
├── docker-compose.yml    # Orchestrates all services
├── .env.example          # Environment variable template
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py       # FastAPI app + CORS + lifespan
│       ├── config.py     # Pydantic Settings (single source of truth)
│       ├── db.py         # SQLAlchemy engine + session
│       ├── models.py     # ORM models (sessions, messages, chunks)
│       ├── routers/
│       │   └── health.py # Health check + chunk stats endpoints
│       └── scripts/
│           └── ingest.py # Transcript ingestion pipeline
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   └── src/
│       ├── App.jsx       # Fetches /health and displays status
│       └── index.css
├── docs/
│   └── architecture.md   # Architecture documentation
└── transcripts/
    └── source/           # Cloned transcript repo (gitignored)
```

## Stopping Services

```bash
docker compose down           # Stop containers
docker compose down -v        # Stop and remove volumes (deletes DB data)
```

## What's Next

- [ ] Chat endpoints and session management
- [x] Transcript ingestion pipeline
- [ ] RAG with pgvector similarity search
- [ ] LLM provider integration (Ollama / Anthropic)
- [ ] Alembic database migrations

