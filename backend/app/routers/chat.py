"""Chat router implementing the RAG query endpoint.

Takes user queries, retrieves relevant chunks from PostgreSQL via pgvector,
constructs a grounded prompt, and calls Ollama's chat endpoint to synthesize
a cited answer.
"""

from typing import Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel
import requests
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.retrieval import search_chunks

router = APIRouter(tags=["chat"])

REFUSAL_MESSAGE = "I don't have enough information from the transcripts to answer that."


class ChatRequest(BaseModel):
    message: str


class SourceCitation(BaseModel):
    source_file: str
    chunk_index: int


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceCitation]
    error: Optional[str] = None


def generate_rag_answer(question: str, chunks: list[dict]) -> tuple[str, Optional[str]]:
    """Format prompt with retrieved context and invoke Ollama's chat API.

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

    url = f"{settings.OLLAMA_BASE_URL}/api/chat"
    payload = {
        "model": settings.OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "stream": False,
        "options": {
            "temperature": 0.2,
        },
    }

    try:
        response = requests.post(url, json=payload, timeout=300)
        response.raise_for_status()
        data = response.json()
        answer = data.get("message", {}).get("content", "").strip()
        if not answer:
            return REFUSAL_MESSAGE, "Empty response from LLM"
        return answer, None
    except requests.exceptions.ConnectionError:
        err = f"Cannot connect to Ollama at {url} — is the model server running?"
        return REFUSAL_MESSAGE, err
    except requests.exceptions.Timeout:
        err = "Ollama generation timed out"
        return REFUSAL_MESSAGE, err
    except Exception as e:
        err = f"Ollama generation error: {e}"
        return REFUSAL_MESSAGE, err


@router.post("/chat", response_model=ChatResponse)
def chat_endpoint(request: ChatRequest, db: Session = Depends(get_db)):
    """Answer questions grounded in the podcast transcripts."""
    user_query = request.message.strip()

    if not user_query:
        return ChatResponse(
            answer="Please ask a question about growth, product management, or startups.",
            sources=[],
        )

    # 1. Retrieve top matching chunks (k=3 provides rich context while keeping inference fast on local machines)
    chunks = search_chunks(query=user_query, db=db, k=3)

    # 2. If no chunks pass the threshold, return structured refusal without LLM call
    if not chunks:
        return ChatResponse(
            answer=REFUSAL_MESSAGE,
            sources=[],
        )

    # 3. Format actual source citations from retrieved chunks
    sources = [
        SourceCitation(
            source_file=c["source_file"],
            chunk_index=c["chunk_index"],
        )
        for c in chunks
    ]

    # 4. Synthesize answer with LLM
    answer, error = generate_rag_answer(user_query, chunks)

    if error:
        return ChatResponse(
            answer=f"Retrieved {len(chunks)} relevant transcript chunks, but LLM generation failed: {error}",
            sources=sources,
            error=error,
        )

    return ChatResponse(
        answer=answer,
        sources=sources if answer != REFUSAL_MESSAGE else [],
        error=None,
    )
