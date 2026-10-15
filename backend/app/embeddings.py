"""Turn text into vectors with Ollama. Shared by ingestion and retrieval so the
SAME model (and the same prefix rule) is used on both sides -- the one rule of
RAG that must never be broken."""

import requests

from app.config import settings
from app.logging_utils import get_logger

log = get_logger("embeddings")

DOC_PREFIX = "search_document: "
QUERY_PREFIX = "search_query: "


class EmbeddingError(ConnectionError):
    """Ollama could not produce embeddings (down, model missing, timeout)."""


def _prepare(texts: list[str], kind: str) -> list[str]:
    if not settings.EMBED_USE_PREFIXES:
        return texts
    prefix = QUERY_PREFIX if kind == "query" else DOC_PREFIX
    return [prefix + t for t in texts]


def _post(inputs: list[str], timeout: int) -> list[list[float]]:
    url = f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/embed"
    try:
        r = requests.post(url, json={"model": settings.OLLAMA_EMBED_MODEL, "input": inputs,
                                     "truncate": True}, timeout=timeout)
        if r.status_code == 404:
            raise EmbeddingError(
                f"Embedding model '{settings.OLLAMA_EMBED_MODEL}' not found. "
                f"Run: ollama pull {settings.OLLAMA_EMBED_MODEL}")
        r.raise_for_status()
        vectors = r.json().get("embeddings") or []
        if len(vectors) != len(inputs):
            raise EmbeddingError(f"Expected {len(inputs)} embeddings, got {len(vectors)}")
        return vectors
    except requests.exceptions.ConnectionError as e:
        raise EmbeddingError(f"Cannot connect to Ollama at {settings.OLLAMA_BASE_URL}") from e
    except requests.exceptions.Timeout as e:
        raise EmbeddingError("Ollama embedding request timed out") from e
    except requests.exceptions.RequestException as e:
        raise EmbeddingError(f"Embedding request failed: {e}") from e


def embed_query(text: str) -> list[float]:
    # Ollama serialises embed calls: during ingestion a query queues behind a
    # 16-chunk batch (~40 s on CPU), so allow the same budget as a batch.
    return _post(_prepare([text], "query"), timeout=180)[0]


def embed_documents(texts: list[str]) -> list[list[float]]:
    """Batch-embed. A batch is ONE HTTP round trip instead of N, which is the
    main reason ingestion is much faster than one-chunk-per-request."""
    out: list[list[float]] = []
    size = max(1, settings.EMBED_BATCH_SIZE)
    for i in range(0, len(texts), size):
        batch = _prepare(texts[i:i + size], "document")
        try:
            out.extend(_post(batch, timeout=180))
        except EmbeddingError as e:
            if len(batch) == 1:
                raise
            log.warning("embed_batch_failed_retrying_singly", extra={"error": str(e)[:200]})
            for single in batch:  # isolate the bad chunk instead of losing the batch
                out.extend(_post([single], timeout=180))
    return out
