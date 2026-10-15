"""Ingestion against real Postgres, with fake embeddings."""

import pytest

from app.models import Chunk, Episode
from app.scripts import ingest

EP = """---
guest: {guest}
title: {title}
youtube_url: https://www.youtube.com/watch?v={vid}
video_id: {vid}
publish_date: 2023-01-02
duration_seconds: 600
keywords:
- growth
---

# {title}

## Transcript

{guest} (00:00:00):
{body}

Lenny (00:05:00):
{body2}
"""


@pytest.fixture
def repo(tmp_path):
    for slug, guest, vid in [("ann-lee", "Ann Lee", "v1"), ("bob-ray", "Bob Ray", "v2")]:
        d = tmp_path / "episodes" / slug
        d.mkdir(parents=True)
        (d / "transcript.md").write_text(EP.format(
            guest=guest, title=f"About {guest}", vid=vid,
            body="activation retention onboarding " * 40, body2="pricing packaging growth " * 40))
    return tmp_path


def test_ingest_stores_episode_metadata_and_chunks(repo, db):
    assert ingest.run(str(repo), None, 0, False, False) == 0
    eps = {e.slug: e for e in db.query(Episode).all()}
    assert set(eps) == {"ann-lee", "bob-ray"}
    e = eps["ann-lee"]
    assert e.guest == "Ann Lee" and e.youtube_url.endswith("v1") and e.chunk_count >= 1
    chunks = db.query(Chunk).filter(Chunk.episode_id == e.id).order_by(Chunk.chunk_index).all()
    assert len(chunks) == e.chunk_count
    assert chunks[0].start_seconds == 0 and chunks[0].embed_model == "nomic-embed-text"
    assert len(chunks[0].embedding) == 768


def test_rerun_is_idempotent_and_skips(repo, db, capsys):
    ingest.run(str(repo), None, 0, False, False)
    before = db.query(Chunk).count()
    ingest.run(str(repo), None, 0, False, False)
    assert db.query(Chunk).count() == before
    assert "skipped (up to date): 2" in capsys.readouterr().out


def test_force_replaces_without_duplicates(repo, db):
    ingest.run(str(repo), None, 0, False, False)
    before = db.query(Chunk).count()
    ingest.run(str(repo), None, 0, True, False)
    db.expire_all()
    assert db.query(Chunk).count() == before and db.query(Episode).count() == 2


def test_limit_and_offset(repo, db):
    ingest.run(str(repo), 1, 1, False, False)
    assert [e.slug for e in db.query(Episode).all()] == ["bob-ray"]


def test_legacy_chunks_without_metadata_are_replaced(repo, db):
    """Chunks from the first version (no episode_id/embed_model) must be upgraded, not duplicated."""
    from tests.conftest import fake_vector
    db.add(Chunk(source_file="episodes/ann-lee/transcript.md", chunk_index=0, content="old",
                 embedding=fake_vector("old")))
    db.commit()
    ingest.run(str(repo), None, 0, False, False)
    db.expire_all()
    legacy = db.query(Chunk).filter(Chunk.episode_id.is_(None)).count()
    assert legacy == 0 and db.query(Chunk).filter(Chunk.content == "old").count() == 0


def test_failed_episode_is_atomic_and_run_continues(repo, db, monkeypatch):
    from tests.conftest import fake_vector

    def flaky(texts):
        if any("Bob Ray" in t for t in texts):
            raise RuntimeError("embedding exploded")
        return [fake_vector(t) for t in texts]

    monkeypatch.setattr("app.scripts.ingest.embed_documents", flaky)
    code = ingest.run(str(repo), None, 0, False, False)
    assert code == 3                                  # reported as partial failure
    assert [e.slug for e in db.query(Episode).all()] == ["ann-lee"]   # no half-written episode


def test_ollama_down_aborts_cleanly(repo, monkeypatch, capsys):
    from app.embeddings import EmbeddingError

    def down(_):
        raise EmbeddingError("Cannot connect to Ollama")

    monkeypatch.setattr("app.scripts.ingest.embed_documents", down)
    assert ingest.run(str(repo), None, 0, False, False) == 2
    assert "Cannot connect to Ollama" in capsys.readouterr().err


def test_dry_run_touches_nothing(repo, db):
    assert ingest.run(str(repo), None, 0, False, True) == 0
    assert db.query(Episode).count() == 0
