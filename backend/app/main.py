"""FastAPI application entry point.

Creates tables on startup (suitable for early development — replace with
Alembic migrations once the schema stabilizes).
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.config import settings
from app.db import Base, engine
from app.routers import health, chat

# Import models so that Base.metadata knows about them before create_all
import app.models  # noqa: F401


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create database tables on startup. In production, use Alembic migrations."""
    # Enable pgvector extension before creating tables that use Vector columns
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Lenny Growth Assistant API",
    description="Backend API for the Lenny Growth Assistant — a RAG-powered podcast chat app.",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — allow the Vite dev server and common local origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(health.router)
app.include_router(chat.router)

