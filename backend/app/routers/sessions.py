"""Sessions: independent conversations with persisted history."""

import uuid
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session as DbSession

from app.db import get_db
from app.errors import AppError
from app.models import Message, Session

router = APIRouter(prefix="/sessions", tags=["sessions"])


class CreateSessionRequest(BaseModel):
    metadata: Optional[dict[str, Any]] = None


class CreateSessionResponse(BaseModel):
    session_id: uuid.UUID
    created_at: datetime


class SessionSummary(BaseModel):
    id: uuid.UUID
    created_at: datetime
    last_activity: datetime
    title: str
    message_count: int


class MessageResponse(BaseModel):
    id: uuid.UUID
    role: str
    content: str
    mode: Optional[str] = None
    sources: Optional[list[dict[str, Any]]] = None
    artifact: Optional[dict[str, Any]] = None
    meta: Optional[dict[str, Any]] = None
    created_at: datetime


def _get_or_404(db: DbSession, session_id: uuid.UUID) -> Session:
    s = db.get(Session, session_id)
    if not s:
        raise AppError("session_not_found", f"Session {session_id} not found", 404)
    return s


@router.post("", response_model=CreateSessionResponse, status_code=status.HTTP_201_CREATED)
def create_session(request: Request, body: Optional[CreateSessionRequest] = None,
                   db: DbSession = Depends(get_db)):
    """New chat = new session = independent context. Stores light user metadata."""
    meta = {"user_agent": request.headers.get("user-agent"),
            "client": (body.metadata if body else None)}
    s = Session(metadata_=meta)
    db.add(s)
    db.commit()
    db.refresh(s)
    return CreateSessionResponse(session_id=s.id, created_at=s.created_at)


@router.get("", response_model=list[SessionSummary])
def list_sessions(limit: int = 30, db: DbSession = Depends(get_db)):
    """Most recent chats first (the history menu)."""
    limit = max(1, min(limit, 100))
    rows = (db.query(Session.id, Session.created_at, func.count(Message.id),
                     func.max(Message.created_at))
            .outerjoin(Message, Message.session_id == Session.id)
            .group_by(Session.id).all())
    out = []
    for sid, created, count, last in rows:
        first = (db.query(Message.content).filter(Message.session_id == sid, Message.role == "user")
                 .order_by(Message.created_at.asc()).first())
        title = (" ".join(first[0].split())[:60] if first else "New chat")
        out.append(SessionSummary(id=sid, created_at=created, last_activity=last or created,
                                  title=title, message_count=count))
    out.sort(key=lambda s: s.last_activity, reverse=True)
    return out[:limit]


@router.get("/{session_id}/messages", response_model=list[MessageResponse])
def get_session_messages(session_id: uuid.UUID, db: DbSession = Depends(get_db)):
    _get_or_404(db, session_id)
    rows = (db.query(Message).filter(Message.session_id == session_id)
            .order_by(Message.created_at.asc()).all())
    return [MessageResponse(id=m.id, role=m.role, content=m.content, mode=m.mode,
                            sources=m.sources, artifact=m.artifact, meta=m.meta,
                            created_at=m.created_at) for m in rows]


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(session_id: uuid.UUID, db: DbSession = Depends(get_db)):
    db.delete(_get_or_404(db, session_id))
    db.commit()
