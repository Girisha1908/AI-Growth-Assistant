"""POST /chat -- the single conversational endpoint.

`mode` picks the skill (ask | explain | quiz | ship30 | artifact | prd); "auto"
lets the router decide from the message. `provider` optionally overrides the
configured model for this one request (the UI's model switcher).
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Literal, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session as DbSession

from app.agent.runner import run_turn
from app.config import get_llm_provider, settings
from app.db import get_db
from app.errors import AppError, provider_error_from
from app.models import Message, Profile, Session

router = APIRouter(tags=["chat"])

Mode = Literal["auto", "ask", "explain", "quiz", "ship30", "artifact", "prd"]
ProviderName = Literal["ollama", "claude", "claude-agent"]


class ChatRequest(BaseModel):
    session_id: uuid.UUID
    message: str = Field(min_length=1, max_length=4000)
    mode: Mode = "auto"
    provider: Optional[ProviderName] = None
    personalize: bool = True

    @field_validator("message")
    @classmethod
    def _not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("message must not be blank")
        return v.strip()


class Source(BaseModel):
    n: int
    episode_id: Optional[str] = None
    guest: Optional[str] = None
    title: Optional[str] = None
    source_file: str
    chunk_index: int
    timestamp: Optional[str] = None
    url: Optional[str] = None
    publish_date: Optional[str] = None
    similarity: Optional[float] = None
    snippet: str


class Artifact(BaseModel):
    type: Literal["markdown", "html"]
    title: str
    content: str


class ChatResponse(BaseModel):
    message_id: uuid.UUID
    session_id: uuid.UUID
    mode: str
    answer: str
    sources: list[Source]
    artifact: Optional[Artifact] = None
    meta: dict[str, Any]


def load_profile(db: DbSession) -> Optional[dict]:
    p = db.get(Profile, 1)
    if not p:
        return None
    data = {"goal": p.goal, "background": p.background, "known_concepts": p.known_concepts or []}
    return data if any(data.values()) else None


async def process_chat(db: DbSession, req: ChatRequest) -> ChatResponse:
    session = db.get(Session, req.session_id)
    if not session:
        raise AppError("session_not_found", f"Session {req.session_id} not found", 404,
                       "Create one with POST /sessions.")

    recent = (db.query(Message).filter(Message.session_id == req.session_id)
              .order_by(Message.created_at.desc()).limit(settings.HISTORY_MESSAGES).all())
    history = [{"role": m.role, "content": m.content} for m in reversed(recent)]

    try:
        provider = get_llm_provider(req.provider)
    except ValueError as e:
        raise provider_error_from(e) from e

    result = await run_turn(db, question=req.message, history=history, mode=req.mode,
                            provider=provider, profile=load_profile(db) if req.personalize else None)

    # Persist only after success, so a failed/timed-out request leaves no half-turn behind.
    # Explicit timestamps: both rows share one transaction, and Postgres now() would tie them.
    now = datetime.now(timezone.utc)
    db.add(Message(session_id=req.session_id, role="user", content=req.message,
                   mode=result["mode"], created_at=now))
    reply = Message(session_id=req.session_id, role="assistant", content=result["answer"],
                    mode=result["mode"], sources=result["sources"], artifact=result["artifact"],
                    meta=result["meta"], created_at=now + timedelta(milliseconds=1))
    db.add(reply)
    db.commit()
    db.refresh(reply)
    return ChatResponse(message_id=reply.id, session_id=req.session_id, mode=result["mode"],
                        answer=result["answer"], sources=result["sources"],
                        artifact=result["artifact"], meta=result["meta"])


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest, db: DbSession = Depends(get_db)):
    return await process_chat(db, req)
