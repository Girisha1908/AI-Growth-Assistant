"""Browse the knowledge base (the Transcripts tab)."""

import uuid
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import String, cast, func, or_
from sqlalchemy.orm import Session

from app.db import get_db
from app.errors import AppError
from app.models import Episode

router = APIRouter(prefix="/episodes", tags=["episodes"])


class EpisodeOut(BaseModel):
    id: uuid.UUID
    slug: str
    guest: Optional[str]
    title: str
    youtube_url: Optional[str]
    publish_date: Optional[date]
    duration_seconds: Optional[int]
    keywords: list[str]
    chunk_count: int
    description: Optional[str] = None


class EpisodePage(BaseModel):
    total: int
    items: list[EpisodeOut]


def _out(e: Episode) -> EpisodeOut:
    return EpisodeOut(id=e.id, slug=e.slug, guest=e.guest, title=e.title, youtube_url=e.youtube_url,
                      publish_date=e.publish_date, duration_seconds=e.duration_seconds,
                      keywords=e.keywords or [], chunk_count=e.chunk_count, description=e.description)


@router.get("", response_model=EpisodePage)
def list_episodes(q: Optional[str] = None, page: int = 1, page_size: int = 24,
                  db: Session = Depends(get_db)):
    page, page_size = max(1, page), max(1, min(page_size, 100))
    query = db.query(Episode).filter(Episode.chunk_count > 0)
    if q and q.strip():
        like = f"%{q.strip()}%"
        query = query.filter(or_(Episode.guest.ilike(like), Episode.title.ilike(like),
                                 cast(Episode.keywords, String).ilike(like)))
    total = query.with_entities(func.count(Episode.id)).scalar() or 0
    rows = (query.order_by(Episode.publish_date.desc().nullslast(), Episode.guest.asc())
            .offset((page - 1) * page_size).limit(page_size).all())
    return EpisodePage(total=total, items=[_out(e) for e in rows])


@router.get("/{episode_id}", response_model=EpisodeOut)
def get_episode(episode_id: uuid.UUID, db: Session = Depends(get_db)):
    e = db.get(Episode, episode_id)
    if not e:
        raise AppError("episode_not_found", "Episode not found", 404)
    return _out(e)
