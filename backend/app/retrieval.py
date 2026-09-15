"""Semantic retrieval over transcript chunks using pgvector and Ollama embeddings.

This module embeds search queries using the same embedding model used during
ingestion (nomic-embed-text) and executes cosine distance similarity queries
against the PostgreSQL `chunks` table via SQLAlchemy.
"""

from typing import Any
import requests
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Chunk


# Tunable similarity threshold:
# pgvector's `<=>` operator computes cosine distance in [0, 2]:
#   distance = 1 - cosine_similarity
#
# Lower distance means higher semantic similarity.
# - A closely matching chunk typically scores distance < 0.38 (similarity > 0.62).
# - Unrelated queries (e.g. "capital of France") score distance > 0.46.
#
# Default threshold: 0.45 (equivalent to cosine similarity >= 0.55).
# Results with distance greater than this threshold are considered "not found".
MAX_DISTANCE_THRESHOLD: float = 0.45


def get_query_embedding(text: str) -> list[float] | None:
    """Call Ollama's embedding API to generate a vector for a search query.

    Returns None if Ollama is unreachable or the embedding request fails.
    """
    url = f"{settings.OLLAMA_BASE_URL}/api/embed"
    try:
        response = requests.post(
            url,
            json={"model": settings.OLLAMA_EMBED_MODEL, "input": text},
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        embeddings = data.get("embeddings")
        if embeddings and len(embeddings) > 0:
            return embeddings[0]
        embedding = data.get("embedding")
        if embedding:
            return embedding
        return None
    except Exception as e:
        print(f"⚠ Embedding retrieval error: {e}")
        return None


def search_chunks(
    query: str,
    db: Session,
    k: int = 5,
    distance_threshold: float = MAX_DISTANCE_THRESHOLD,
) -> list[dict[str, Any]]:
    """Retrieve top-k most relevant transcript chunks for a user query.

    Args:
        query: The user's search text.
        db: SQLAlchemy database session.
        k: Maximum number of chunks to return (default: 5).
        distance_threshold: Maximum allowable cosine distance. Chunks with
            distance > distance_threshold are filtered out.

    Returns:
        A list of dictionaries containing chunk content, source file,
        chunk index, and distance metric, ordered by ascending distance.
        If no chunks meet the threshold, returns an empty list.
    """
    query_vector = get_query_embedding(query)
    if query_vector is None:
        return []

    # SQLAlchemy query using pgvector's cosine_distance (<=> operator)
    # distance = Chunk.embedding.cosine_distance(query_vector)
    distance_expr = Chunk.embedding.cosine_distance(query_vector).label("distance")

    results = (
        db.query(
            Chunk.id,
            Chunk.source_file,
            Chunk.chunk_index,
            Chunk.content,
            distance_expr,
        )
        .order_by(distance_expr.asc())
        .limit(k)
        .all()
    )

    if not results:
        return []

    # Gating check: if even the top result does not meet the similarity threshold,
    # treat the query as having "no good match" to prevent hallucination.
    top_distance = results[0].distance
    if top_distance is not None and top_distance > distance_threshold:
        return []

    # Filter any individual results that exceed the threshold
    matched_chunks = []
    for row in results:
        if row.distance is not None and row.distance <= distance_threshold:
            matched_chunks.append({
                "id": str(row.id),
                "source_file": row.source_file,
                "chunk_index": row.chunk_index,
                "content": row.content,
                "distance": float(row.distance),
                "similarity": float(1.0 - row.distance),
            })

    return matched_chunks
