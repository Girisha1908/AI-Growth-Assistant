"""Hybrid retrieval: vector search + keyword search, fused, then gated.

  question ──embed──▶ vector search (pgvector, cosine)   ─┐
      │                                                   ├─▶ RRF fusion ─▶ gate ─▶ top-k
      └──terms───▶ keyword search (Postgres full-text)   ─┘

Why both?  Vectors capture MEANING ("how to keep users" ≈ "retention") but blur
exact names/terms ("Brian Chesky", "RICE"). Keywords catch those exactly.

Why a gate?  If even the closest chunk is not close enough, the corpus does not
contain the answer. We refuse BEFORE calling the LLM: a small model handed weak
context will happily make something up.
"""

import re
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.embeddings import embed_query
from app.ingestion.parsing import format_timestamp, timestamp_url
from app.logging_utils import get_logger

log = get_logger("retrieval")

RRF_K = 60  # standard constant from the Reciprocal Rank Fusion paper
STOPWORDS = set("""a an and are as at be but by can could do does for from had has have how i if in
into is it its me my of on or our should so than that the their them then there these they this to
us was we were what when where which who why will with would you your about tell explain give
please me like just""".split())

_COLUMNS = """c.id, c.episode_id, c.source_file, c.chunk_index, c.content, c.start_seconds,
       e.slug, e.guest, e.title, e.youtube_url, e.publish_date,
       (c.embedding <=> CAST(:qvec AS vector)) AS distance"""

_VECTOR_SQL = text(f"""
SELECT {_COLUMNS}
FROM chunks c LEFT JOIN episodes e ON e.id = c.episode_id
ORDER BY c.embedding <=> CAST(:qvec AS vector)
LIMIT :n
""")

_KEYWORD_SQL = text(f"""
SELECT {_COLUMNS}
FROM chunks c LEFT JOIN episodes e ON e.id = c.episode_id,
     to_tsquery('english', :tsq) q
WHERE c.tsv @@ q
ORDER BY ts_rank_cd(c.tsv, q) DESC
LIMIT :n
""")


@dataclass
class Retrieval:
    chunks: list[dict[str, Any]] = field(default_factory=list)
    best_distance: Optional[float] = None
    reason: str = "ok"  # ok | below_threshold | no_chunks
    ms: int = 0
    vector_hits: int = 0
    keyword_hits: int = 0


# ── pure helpers (unit-tested without a database) ───────────────────────
def keyword_query(question: str, max_terms: int = 8) -> Optional[str]:
    """'What is a North Star metric?' -> 'north | star | metric'  (OR query)."""
    seen, terms = set(), []
    for tok in re.findall(r"[A-Za-z0-9]+", question.lower()):
        if len(tok) < 2 or tok in STOPWORDS or tok in seen:
            continue
        seen.add(tok)
        terms.append(tok)
    return " | ".join(terms[:max_terms]) or None


def build_retrieval_query(prior_user_messages: list[str], message: str) -> str:
    """Short follow-ups ('what about the first week?') carry no topic by
    themselves, so prepend the previous user question. Long messages stand alone."""
    if prior_user_messages and len(message.split()) <= 8:
        return f"{prior_user_messages[-1]} {message}"
    return message


def rrf_scores(ranked_lists: list[list[str]], k: int = RRF_K) -> dict[str, float]:
    """Reciprocal Rank Fusion: score = Σ 1/(k + rank). Rank-based, so vector
    distances and keyword scores (different scales) combine fairly."""
    scores: dict[str, float] = {}
    for ranked in ranked_lists:
        for rank, cid in enumerate(ranked, 1):
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank)
    return scores


def fuse_and_select(vector_rows: list[dict], keyword_rows: list[dict], *, top_k: int,
                    threshold: float, margin: float, max_per_episode: int) -> list[dict]:
    by_id = {r["id"]: r for r in vector_rows}
    for r in keyword_rows:
        by_id.setdefault(r["id"], r)
    fused = rrf_scores([[r["id"] for r in vector_rows], [r["id"] for r in keyword_rows]])
    keyword_ids = {r["id"] for r in keyword_rows}
    picked, per_episode = [], {}
    for cid in sorted(fused, key=fused.get, reverse=True):
        row = by_id[cid]
        limit = threshold + (margin if cid in keyword_ids else 0.0)
        if row["distance"] > limit:
            continue  # keyword matched, but the meaning is too far from the question
        ep = row.get("episode_id") or row["source_file"]
        if per_episode.get(ep, 0) >= max_per_episode:
            continue  # keep results diverse: don't let one episode fill every slot
        per_episode[ep] = per_episode.get(ep, 0) + 1
        picked.append({**row, "score": fused[cid]})
        if len(picked) >= top_k:
            break
    return picked


def decorate(row: dict) -> dict:
    """Add display fields (similarity, timestamp, deep link)."""
    row = dict(row)
    row["similarity"] = round(1.0 - float(row["distance"]), 4)
    row["timestamp"] = format_timestamp(row.get("start_seconds"))
    row["url"] = timestamp_url(row.get("youtube_url"), row.get("start_seconds"))
    return row


def public_source(n: int, row: dict) -> dict:
    """What the API/UI sees for a citation (`n` matches the [n] markers in answers)."""
    pub = row.get("publish_date")
    return {
        "n": n,
        "episode_id": str(row["episode_id"]) if row.get("episode_id") else None,
        "guest": row.get("guest"),
        "title": row.get("title"),
        "source_file": row["source_file"],
        "chunk_index": row["chunk_index"],
        "timestamp": row.get("timestamp"),
        "url": row.get("url"),
        "publish_date": pub.isoformat() if pub else None,
        "similarity": row.get("similarity"),
        "snippet": " ".join(row["content"].split())[:320],
    }


# ── database-backed search ──────────────────────────────────────────────
def _vec_literal(vec: list[float]) -> str:
    return "[" + ",".join(f"{x:.7g}" for x in vec) + "]"


def search_chunks(query: str, db: Session, k: Optional[int] = None,
                  distance_threshold: Optional[float] = None) -> Retrieval:
    """Raises EmbeddingError if Ollama cannot embed the query (caller maps it to 503)."""
    k = k or settings.RETRIEVAL_TOP_K
    threshold = settings.RELEVANCE_MAX_DISTANCE if distance_threshold is None else distance_threshold
    t0 = time.perf_counter()

    qvec = _vec_literal(embed_query(query))
    n = settings.RETRIEVAL_CANDIDATES
    vector_rows = [dict(r._mapping) for r in db.execute(_VECTOR_SQL, {"qvec": qvec, "n": n})]
    if not vector_rows:
        return Retrieval(reason="no_chunks", ms=round((time.perf_counter() - t0) * 1000))
    best = float(vector_rows[0]["distance"])

    result = Retrieval(best_distance=round(best, 4), vector_hits=len(vector_rows))
    if best > threshold:  # THE GATE: nothing in the corpus is close enough
        result.reason = "below_threshold"
    else:
        tsq = keyword_query(query)
        keyword_rows = []
        if tsq:
            keyword_rows = [dict(r._mapping) for r in
                            db.execute(_KEYWORD_SQL, {"qvec": qvec, "tsq": tsq, "n": n})]
        result.keyword_hits = len(keyword_rows)
        picked = fuse_and_select(vector_rows, keyword_rows, top_k=k, threshold=threshold,
                                 margin=settings.KEYWORD_DISTANCE_MARGIN,
                                 max_per_episode=settings.MAX_CHUNKS_PER_EPISODE)
        result.chunks = [decorate(r) for r in picked]
    result.ms = round((time.perf_counter() - t0) * 1000)
    log.info("retrieval", extra={"query_chars": len(query), "reason": result.reason,
                                 "returned": len(result.chunks), "best_distance": result.best_distance,
                                 "vector_hits": result.vector_hits,
                                 "keyword_hits": result.keyword_hits, "ms": result.ms})
    return result
