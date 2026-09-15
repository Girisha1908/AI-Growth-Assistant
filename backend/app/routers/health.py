"""Health check endpoint that performs a real database connectivity test.

This router does NOT return hardcoded values — it runs a real SQL query
against PostgreSQL and reports the actual state of the system.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db

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
