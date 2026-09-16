"""Router for specialized content generation skills.

Exposes endpoints for advanced generation workflows such as the Ship 30 essay writer,
integrating with PostgreSQL sessions and pgvector retrieval.
"""

import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session as DbSession

from app.db import get_db
from app.models import Session, Message
from app.retrieval import search_chunks
from app.skills.ship30 import generate_ship30_essay, REFUSAL_MESSAGE

router = APIRouter(prefix="/skills", tags=["skills"])


class Ship30Request(BaseModel):
    session_id: uuid.UUID
    topic: str


class SourceCitation(BaseModel):
    source_file: str
    chunk_index: int


class Ship30Response(BaseModel):
    essay: str
    sources: list[SourceCitation]
    word_count: int
    error: Optional[str] = None


@router.post("/ship30", response_model=Ship30Response)
async def ship30_endpoint(request: Ship30Request, db: DbSession = Depends(get_db)):
    """Generate a grounded, highly structured Ship 30 for 30 essay on a podcast topic."""
    # 1. Validate session existence
    session = db.query(Session).filter(Session.id == request.session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {request.session_id} not found",
        )

    topic = request.topic.strip()
    if not topic:
        return Ship30Response(
            essay="Please provide a specific topic or theme for the Ship 30 essay.",
            sources=[],
            word_count=0,
        )

    # 2. Persist user turn in messages table
    user_record = Message(
        session_id=request.session_id,
        role="user",
        content=f"Ship 30 Essay: {topic}",
    )
    db.add(user_record)
    db.commit()

    # 3. Retrieve relevant chunks using existing retrieval pipeline (k=3 provides rich context while keeping CPU inference fast)
    chunks = search_chunks(query=topic, db=db, k=3)

    if not chunks:
        asst_record = Message(
            session_id=request.session_id,
            role="assistant",
            content=REFUSAL_MESSAGE,
        )
        db.add(asst_record)
        db.commit()
        return Ship30Response(
            essay=REFUSAL_MESSAGE,
            sources=[],
            word_count=len(REFUSAL_MESSAGE.split()),
        )

    # 4. Format source citations
    sources = [
        SourceCitation(
            source_file=c["source_file"],
            chunk_index=c["chunk_index"],
        )
        for c in chunks
    ]

    # 5. Synthesize Ship 30 essay via LLMProvider
    essay, error = await generate_ship30_essay(topic=topic, chunks=chunks)

    final_essay = (
        f"Retrieved {len(chunks)} relevant transcript chunks, but essay generation failed: {error}"
        if error
        else essay
    )

    # 6. Persist assistant essay in messages table
    asst_record = Message(
        session_id=request.session_id,
        role="assistant",
        content=final_essay,
    )
    db.add(asst_record)
    db.commit()

    word_count = len(final_essay.split())

    return Ship30Response(
        essay=final_essay,
        sources=sources if essay != REFUSAL_MESSAGE else [],
        word_count=word_count,
        error=error,
    )
