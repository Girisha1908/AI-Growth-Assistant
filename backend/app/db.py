"""Database engine, session factory, and declarative base setup."""

from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.config import settings

# pool_pre_ping enables connection health checks before queries are dispatched
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """Dependency that yields a SQLAlchemy database session and ensures clean closure."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
