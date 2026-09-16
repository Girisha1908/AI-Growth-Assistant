"""Router for session management and conversation history retrieval.

Provides endpoints to create new conversation sessions and retrieve the full
message history for any given session.
"""

import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session as DbSession

from app.db import get_db
from app.models import Session, Message

router = APIRouter(prefix="/sessions", tags=["sessions"])


class CreateSessionResponse(BaseModel):
    session_id: uuid.UUID


class MessageResponse(BaseModel):
    id: uuid.UUID
    role: str
    content: str
    created_at: datetime


@router.post("", response_model=CreateSessionResponse, status_code=status.HTTP_201_CREATED)
def create_session(db: DbSession = Depends(get_db)):
    """Create a new interactive chat session and return its unique ID."""
    session = Session()
    db.add(session)
    db.commit()
    db.refresh(session)
    return CreateSessionResponse(session_id=session.id)


@router.get("/{session_id}/messages", response_model=list[MessageResponse])
def get_session_messages(session_id: uuid.UUID, db: DbSession = Depends(get_db)):
    """Retrieve full chronological message history for a session."""
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )

    messages = (
        db.query(Message)
        .filter(Message.session_id == session_id)
        .order_by(Message.created_at.asc())
        .all()
    )

    return [
        MessageResponse(
            id=m.id,
            role=m.role,
            content=m.content,
            created_at=m.created_at,
        )
        for m in messages
    ]
