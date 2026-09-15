# 🚀 Lenny Growth Assistant

A RAG-powered AI chat assistant built on podcast transcripts. This repository contains the foundational skeleton — a containerized FastAPI backend with PostgreSQL (pgvector) and a minimal React health-check frontend.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) (v20+)
- [Docker Compose](https://docs.docker.com/compose/install/) (v2+)

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
   | API Docs | http://localhost:8000/docs     |

   The frontend should display live health data fetched from the FastAPI backend, which in turn performs a real database connectivity check against PostgreSQL.

## Architecture

```
┌──────────────┐     ┌──────────────┐     ┌─────────────────────┐
│   Frontend   │────▶│   FastAPI    │────▶│  PostgreSQL + pgvec │
│  (Vite/React)│     │   Backend    │     │      (pg16)         │
│  :5173       │     │  :8000       │     │  :5432              │
└──────────────┘     └──────────────┘     └─────────────────────┘
```

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
│       ├── models.py     # ORM models (sessions, messages)
│       └── routers/
│           └── health.py # Real DB health check endpoint
└── frontend/
    ├── Dockerfile
    ├── package.json
    └── src/
        ├── App.jsx       # Fetches /health and displays status
        └── index.css
```

## Stopping Services

```bash
docker compose down           # Stop containers
docker compose down -v        # Stop and remove volumes (deletes DB data)
```

## What's Next

- [ ] Chat endpoints and session management
- [ ] Transcript ingestion pipeline
- [ ] RAG with pgvector embeddings
- [ ] LLM provider integration (Ollama / Anthropic)
- [ ] Alembic database migrations
