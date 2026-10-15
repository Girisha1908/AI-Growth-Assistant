"""POST /search -- retrieval only (no LLM). Fast, free, and exactly what the eval
set needs to measure grounding and refusal without waiting on a slow local model."""

from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.embeddings import EmbeddingError
from app.errors import ProviderError
from app.retrieval import public_source, search_chunks
from app.routers.chat import Source

router = APIRouter(tags=["search"])


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=1000)
    k: Optional[int] = Field(default=None, ge=1, le=20)


class SearchResponse(BaseModel):
    reason: str                      # ok | below_threshold | no_chunks
    answerable: bool                 # would /chat call the model? (False => refusal)
    best_distance: Optional[float]
    sources: list[Source]
    ms: int


@router.post("/search", response_model=SearchResponse)
def search(req: SearchRequest, db: Session = Depends(get_db)):
    try:
        r = search_chunks(req.query.strip(), db, k=req.k)
    except EmbeddingError as e:
        raise ProviderError("embedding_unavailable", str(e), 503,
                            "Start Ollama and make sure the embedding model is pulled.") from e
    return SearchResponse(reason=r.reason, answerable=bool(r.chunks), best_distance=r.best_distance,
                          sources=[public_source(n, c) for n, c in enumerate(r.chunks, 1)], ms=r.ms)
