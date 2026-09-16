"""Chat router implementing the RAG query endpoint.

Takes user queries, retrieves relevant chunks from PostgreSQL via pgvector,
constructs a grounded prompt, and calls the configured LLMProvider interface
to synthesize a cited answer with session persistence.
"""

import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session as DbSession

from app.config import get_llm_provider
from app.db import get_db
from app.models import Session, Message
from app.providers.base import LLMProvider
from app.retrieval import search_chunks

router = APIRouter(tags=["chat"])

REFUSAL_MESSAGE = "I don't have enough information from the transcripts to answer that."


class ChatRequest(BaseModel):
    session_id: uuid.UUID
    message: str


class SourceCitation(BaseModel):
    source_file: str
    chunk_index: int


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceCitation]
    error: Optional[str] = None


async def generate_rag_answer(
    question: str,
    chunks: list[dict],
    history: Optional[list[Message]] = None,
    provider: Optional[LLMProvider] = None,
) -> tuple[str, Optional[str]]:
    """Format prompt with retrieved context and invoke the LLMProvider interface.

    Returns a tuple of (answer_text, error_message).
    """
    # Assemble context passages
    context_blocks = []
    for idx, c in enumerate(chunks, 1):
        context_blocks.append(
            f"--- [Snippet {idx} | Source: {c['source_file']} (chunk {c['chunk_index']})] ---\n"
            f"{c['content']}"
        )
    context_str = "\n\n".join(context_blocks)

    system_prompt = (
        "You are the Lenny Growth Assistant, an AI expert on product management, "
        "growth, and startup leadership built on Lenny's Podcast transcripts.\n\n"
        "INSTRUCTIONS:\n"
        "1. Answer the user's question using ONLY the provided transcript snippets below.\n"
        "2. If the provided snippets do not contain enough facts to answer the question, "
        f"you MUST reply with: '{REFUSAL_MESSAGE}'\n"
        "3. Do NOT make up information or use prior knowledge not contained in the context.\n"
        "4. Be concise, direct, and authoritative in your response."
    )

    user_message = (
        f"Context from podcast transcripts:\n\n{context_str}\n\n"
        f"Question: {question}\n\n"
        "Answer based only on the context above:"
    )

    # Construct chat messages list, including system prompt, previous conversation turns, and current query
    messages = [{"role": "system", "content": system_prompt}]
    if history:
        for msg in history:
            messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": user_message})

    llm = provider or get_llm_provider()
    try:
        answer = await llm.chat(messages)
        if not answer:
            return REFUSAL_MESSAGE, "Empty response from LLM"
        return answer, None
    except Exception as e:
        return REFUSAL_MESSAGE, str(e)


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest, db: DbSession = Depends(get_db)):
    """Answer questions grounded in the podcast transcripts with session persistence."""
    # 1. Validate session existence — return 404 if invalid
    session = db.query(Session).filter(Session.id == request.session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {request.session_id} not found",
        )

    user_query = request.message.strip()
    if not user_query:
        return ChatResponse(
            answer="Please ask a question about growth, product management, or startups.",
            sources=[],
        )

    # 2. Retrieve recent conversation history for this session (last 6 messages)
    recent_messages = (
        db.query(Message)
        .filter(Message.session_id == request.session_id)
        .order_by(Message.created_at.desc())
        .limit(6)
        .all()
    )
    history = list(reversed(recent_messages))

    # 3. Inform retrieval using conversation context for follow-up questions
    prior_user_queries = [m.content for m in history if m.role == "user"]
    retrieval_query = (
        f"{prior_user_queries[-1]} {user_query}" if prior_user_queries else user_query
    )

    chunks = search_chunks(query=retrieval_query, db=db, k=3)
    if not chunks and prior_user_queries:
        # Fallback to standalone user query if combined context had no matches
        chunks = search_chunks(query=user_query, db=db, k=3)

    # 4. Save user message to database
    user_record = Message(
        session_id=request.session_id,
        role="user",
        content=user_query,
    )
    db.add(user_record)
    db.commit()

    # 5. If no chunks pass the threshold, return refusal and persist assistant response
    if not chunks:
        asst_record = Message(
            session_id=request.session_id,
            role="assistant",
            content=REFUSAL_MESSAGE,
        )
        db.add(asst_record)
        db.commit()
        return ChatResponse(
            answer=REFUSAL_MESSAGE,
            sources=[],
        )

    # 6. Format source citations
    sources = [
        SourceCitation(
            source_file=c["source_file"],
            chunk_index=c["chunk_index"],
        )
        for c in chunks
    ]

    # 7. Synthesize answer using the swappable LLMProvider interface
    answer, error = await generate_rag_answer(user_query, chunks, history=history)

    final_answer = (
        f"Retrieved {len(chunks)} relevant transcript chunks, but LLM generation failed: {error}"
        if error
        else answer
    )

    # 8. Save assistant response to database
    asst_record = Message(
        session_id=request.session_id,
        role="assistant",
        content=final_answer,
    )
    db.add(asst_record)
    db.commit()

    return ChatResponse(
        answer=final_answer,
        sources=sources if answer != REFUSAL_MESSAGE else [],
        error=error,
    )
