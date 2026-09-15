"""Health check endpoints that perform real database connectivity tests.

This router does NOT return hardcoded values — it runs real SQL queries
against PostgreSQL and reports the actual state of the system.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import text, func
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models import Chunk

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    """Check system health by verifying database connectivity.

    Returns:
        - status "ok" if the DB query succeeds
        - status "degraded" with an error message if the DB is unreachable
    """
    # Attempt a real database query to verify connectivity
    try:
        db.execute(text("SELECT 1"))
        db_status = "connected"
        status = "ok"
        error = None
    except Exception as e:
        db_status = "disconnected"
        status = "degraded"
        error = str(e)

    response = {
        "status": status,
        "database": db_status,
        "provider": settings.LLM_PROVIDER,
    }

    if error:
        response["error"] = error

    return response


@router.get("/health/chunks")
def chunks_health(db: Session = Depends(get_db)):
    """Return ingestion stats: total chunks, unique sources, and a sample source.

    Useful for verifying that the ingestion pipeline ran successfully
    without needing to query Postgres directly.
    """
    try:
        total = db.query(func.count(Chunk.id)).scalar() or 0
        unique_sources = db.query(func.count(func.distinct(Chunk.source_file))).scalar() or 0

        sample = None
        if total > 0:
            sample = db.query(Chunk.source_file).limit(1).scalar()

        return {
            "total_chunks": total,
            "unique_sources": unique_sources,
            "sample_source": sample,
        }
    except Exception as e:
        return {
            "total_chunks": 0,
            "unique_sources": 0,
            "sample_source": None,
            "error": str(e),
        }

