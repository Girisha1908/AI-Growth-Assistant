"""Dedicated skill endpoints (thin wrappers over the same agent as /chat)."""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.db import get_db
from app.routers.chat import ChatRequest, ChatResponse, ProviderName, process_chat

router = APIRouter(prefix="/skills", tags=["skills"])


class Ship30Request(BaseModel):
    session_id: uuid.UUID
    topic: str = Field(min_length=1, max_length=1000)
    provider: Optional[ProviderName] = None


@router.post("/ship30", response_model=ChatResponse)
async def ship30(req: Ship30Request, db=Depends(get_db)):
    """Generate a Ship 30 for 30 essay (artifact) grounded in the transcripts."""
    return await process_chat(db, ChatRequest(session_id=req.session_id, message=req.topic,
                                              mode="ship30", provider=req.provider))
