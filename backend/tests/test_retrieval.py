from app.config import settings
from app.retrieval import (build_retrieval_query, fuse_and_select, keyword_query, public_source,
                           rrf_scores, search_chunks)


# ── pure logic ──────────────────────────────────────────────────────────
def test_keyword_query():
    assert keyword_query("What is a North Star metric?") == "north | star | metric"
    assert keyword_query("the and of") is None
    assert keyword_query("RICE RICE framework") == "rice | framework"


def test_followup_query_building():
    assert build_retrieval_query(["How to improve retention?"], "what about week one?") \
        == "How to improve retention? what about week one?"
    long = "Explain in detail how pricing experiments were designed at the company"
    assert build_retrieval_query(["earlier"], long) == long
    assert build_retrieval_query([], "short one") == "short one"


def test_rrf_prefers_items_in_both_lists():
    scores = rrf_scores([["a", "b", "c"], ["c", "a"]])
    assert max(scores, key=scores.get) == "a" or scores["a"] > scores["b"]
    assert scores["a"] > scores["b"] and scores["c"] > scores["b"]


def _row(i, d, ep="e1"):
    return {"id": i, "distance": d, "episode_id": ep, "source_file": f"f{ep}"}


def test_fuse_threshold_margin_and_diversity():
    vec = [_row("v1", 0.30, "e1"), _row("v2", 0.35, "e1"), _row("v3", 0.40, "e1"), _row("v4", 0.60, "e2")]
    kw = [_row("k1", 0.50, "e3"), _row("k2", 0.70, "e4")]
    out = fuse_and_select(vec, kw, top_k=10, threshold=0.45, margin=0.10, max_per_episode=2)
    ids = [r["id"] for r in out]
    assert "v4" not in ids                       # too far, vector-only
    assert "k1" in ids                           # keyword hit allowed within margin
    assert "k2" not in ids                       # beyond threshold+margin
    assert sum(1 for r in out if r["episode_id"] == "e1") == 2   # per-episode cap


# ── against real Postgres + pgvector ────────────────────────────────────
def test_relevant_query_returns_cited_chunks(db, corpus):
    r = search_chunks("retention first week users activation", db)
    assert r.reason == "ok" and r.chunks
    top = r.chunks[0]
    assert top["guest"] == "Albert Cheng" and top["similarity"] > 0.55
    assert top["url"] == "https://youtu.be/BBB?t=12s" and top["timestamp"] == "0:12"


def test_off_topic_is_gated(db, corpus):
    r = search_chunks("capital city france paris", db)
    assert r.chunks == [] and r.reason == "below_threshold"


def test_empty_database(db):
    assert search_chunks("anything at all", db).reason == "no_chunks"


def test_per_episode_cap_and_public_source(db, corpus):
    r = search_chunks("retention churn onboarding cohorts curve", db, k=5)
    assert sum(1 for c in r.chunks if c["guest"] == "Albert Cheng") <= settings.MAX_CHUNKS_PER_EPISODE
    src = public_source(1, r.chunks[0])
    assert src["n"] == 1 and src["guest"] and src["url"] and len(src["snippet"]) <= 320


def test_keyword_search_runs_and_is_gated_by_vector(db, corpus):
    # 'founder' appears literally; the keyword path must execute without error
    r = search_chunks("founder mode Airbnb", db)
    assert r.keyword_hits >= 1 and r.chunks[0]["guest"] == "Brian Chesky"
