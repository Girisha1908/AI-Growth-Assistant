"""FastAPI entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app.models  # noqa: F401  (register tables on Base.metadata)
from app.config import settings
from app.db import engine
from app.errors import install_error_handlers
from app.logging_utils import RequestLogMiddleware, configure_logging, get_logger
from app.migrate import init_db
from app.routers import chat, client_events, episodes, health, notes, profile, search, sessions, skills

configure_logging(settings.LOG_LEVEL)
log = get_logger("startup")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Resilience: if the DB is briefly unavailable the API still starts; /health
    # reports "degraded" and requests return a structured 503 instead of crashing.
    try:
        init_db(engine)
    except Exception as e:  # noqa: BLE001
        log.error("startup_db_unavailable", extra={"error": str(e)[:300]})
    log.info("startup", extra={"provider": settings.LLM_PROVIDER, "embed": settings.embed_tag})
    yield


app = FastAPI(title="Lenny Growth Assistant API",
              description="Grounded Q&A, Ship 30 essays and artifacts over Lenny's Podcast.",
              version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.CORS_ORIGINS, allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"], expose_headers=["x-request-id"])
app.add_middleware(RequestLogMiddleware)
install_error_handlers(app)

for r in (health.router, chat.router, sessions.router, skills.router, episodes.router,
          notes.router, profile.router, search.router, client_events.router):
    app.include_router(r)
