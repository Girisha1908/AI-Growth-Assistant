"""Health endpoints. Real checks, never hard-coded 200s."""

from fastapi import APIRouter, Depends
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.config import available_providers, get_llm_provider, settings
from app.db import get_db
from app.models import Chunk, Episode

router = APIRouter(tags=["health"])
VERSION = "1.0.0"


@router.get("/health")
async def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        db_status, db_error = "connected", None
    except Exception as e:  # noqa: BLE001
        db_status, db_error = "disconnected", str(e)[:200]

    detail: dict = {"name": settings.LLM_PROVIDER, "model": None, "reachable": False}
    try:
        provider = get_llm_provider()
        detail.update({"name": provider.name, "model": provider.model,
                       "configured": True, **(await provider.ping())})
    except ValueError as e:  # e.g. claude selected but no key
        detail.update({"configured": False, "error": str(e)})

    ok = db_status == "connected" and detail.get("reachable", False)
    body = {"status": "ok" if ok else "degraded", "database": db_status,
            "provider": detail["name"], "provider_detail": detail,
            "embed_model": settings.embed_tag, "version": VERSION}
    if db_error:
        body["error"] = db_error
    return body


@router.get("/health/chunks")
def chunks_health(db: Session = Depends(get_db)):
    """Corpus coverage: lets you verify ingestion without opening psql."""
    try:
        total = db.query(func.count(Chunk.id)).scalar() or 0
        episodes = db.query(func.count(Episode.id)).filter(Episode.chunk_count > 0).scalar() or 0
        legacy = db.query(func.count(Chunk.id)).filter(Chunk.episode_id.is_(None)).scalar() or 0
        tags = [t for (t,) in db.query(Chunk.embed_model).distinct().all()]
        sample = db.query(Chunk.source_file).limit(1).scalar() if total else None
        return {"total_chunks": total, "episodes": episodes,
                "unique_sources": db.query(func.count(func.distinct(Chunk.source_file))).scalar() or 0,
                "sample_source": sample, "embed_models": tags,
                "legacy_chunks_without_metadata": legacy,
                "hint": ("Re-run ingestion to attach episode metadata to legacy chunks."
                         if legacy else None)}
    except Exception as e:  # noqa: BLE001
        return {"total_chunks": 0, "episodes": 0, "unique_sources": 0, "sample_source": None,
                "error": str(e)[:200]}


@router.get("/config")
def public_config():
    """What the UI needs to display honestly (no secrets)."""
    return {"provider": settings.LLM_PROVIDER, "providers": available_providers(),
            "ollama_model": settings.OLLAMA_MODEL, "embed_model": settings.embed_tag,
            "relevance_max_distance": settings.RELEVANCE_MAX_DISTANCE,
            "top_k": settings.RETRIEVAL_TOP_K, "ship30_target_words": settings.SHIP30_TARGET_WORDS,
            "ship30_strategy": settings.SHIP30_STRATEGY, "search": "hybrid (vector + keyword, RRF)"}
