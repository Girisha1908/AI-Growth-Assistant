"""Test harness.

* Uses a REAL PostgreSQL + pgvector database (a separate `lenny_test` DB, created
  on demand) so SQL, indexes and migrations are genuinely exercised.
* Never needs Ollama or any API key: the LLM is a scripted FakeProvider and
  embeddings are a deterministic bag-of-words hash (shared words => similar vectors).
"""

import hashlib
import math
import os
import re
from urllib.parse import urlparse

import pytest
import sqlalchemy as sa

# ── point the app at the test database BEFORE importing it ──────────────
_base = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/lenny_growth")
_u = urlparse(_base)
TEST_DB = "lenny_test"
TEST_URL = _base.replace(_u.path, f"/{TEST_DB}")
ADMIN_URL = _base.replace(_u.path, "/postgres")
os.environ["DATABASE_URL"] = TEST_URL
os.environ.pop("ANTHROPIC_API_KEY", None)

_admin = sa.create_engine(ADMIN_URL, isolation_level="AUTOCOMMIT")
with _admin.connect() as c:
    if not c.execute(sa.text("SELECT 1 FROM pg_database WHERE datname=:n"), {"n": TEST_DB}).scalar():
        c.execute(sa.text(f'CREATE DATABASE "{TEST_DB}"'))
_admin.dispose()

from fastapi.testclient import TestClient  # noqa: E402

from app.config import settings  # noqa: E402
from app.db import SessionLocal, engine  # noqa: E402
from app.migrate import init_db  # noqa: E402
from app.providers.base import LLMProvider  # noqa: E402

STOP = set("the a an and of to in is are for on with how what why do does should i it that this".split())


def fake_vector(text: str) -> list[float]:
    """Bag-of-words hashing into 768 dims, L2-normalised."""
    vec = [0.0] * 768
    for tok in re.findall(r"[a-z0-9]+", text.lower()):
        if len(tok) > 2 and tok not in STOP:
            vec[int(hashlib.md5(tok.encode()).hexdigest(), 16) % 768] += 1.0
    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / norm for x in vec]


class FakeProvider(LLMProvider):
    name = "fake"
    model = "fake-1"

    def __init__(self, script=None, fail_with=None):
        self.script = list(script or [])
        self.fail_with = fail_with
        self.calls: list[list[dict]] = []

    async def chat(self, messages):
        self.calls.append(messages)
        if self.fail_with:
            raise self.fail_with
        if self.script:
            return self.script.pop(0)
        return "Answer grounded in the excerpts [1]."

    async def ping(self):
        return {"reachable": True}


@pytest.fixture(scope="session", autouse=True)
def _schema():
    init_db(engine)
    yield


@pytest.fixture(autouse=True)
def _clean_db(_schema):
    with engine.begin() as conn:
        conn.execute(sa.text("TRUNCATE chunks, episodes, messages, sessions, profile, notes CASCADE"))
    yield


@pytest.fixture(autouse=True)
def _fake_embeddings(monkeypatch):
    monkeypatch.setattr("app.retrieval.embed_query", fake_vector)
    monkeypatch.setattr("app.scripts.ingest.embed_documents", lambda texts: [fake_vector(t) for t in texts])


@pytest.fixture
def provider(monkeypatch):
    p = FakeProvider()
    monkeypatch.setattr("app.routers.chat.get_llm_provider", lambda name=None: p)
    monkeypatch.setattr("app.routers.health.get_llm_provider", lambda name=None: p)
    return p


@pytest.fixture
def client(provider):
    from app.main import app
    with TestClient(app) as c:
        yield c


@pytest.fixture
def db():
    s = SessionLocal()
    yield s
    s.close()


@pytest.fixture
def corpus(db):
    """Three tiny episodes with short chunks (so fake-embedding similarity is high)."""
    from app.models import Chunk, Episode

    data = [
        ("brian-chesky", "Brian Chesky", "Founder mode at Airbnb", "https://youtu.be/AAA", [
            (0, 0, "founder mode product reviews craft Airbnb leadership"),
            (1, 90, "Airbnb roadmap weekly review founder mode quality"),
        ]),
        ("albert-cheng", "Albert Cheng", "Retention in subscription products", "https://youtu.be/BBB", [
            (0, 12, "retention first week users activation habit"),
            (1, 300, "churn subscription retention onboarding experience"),
            (2, 600, "retention cohorts curve flatten"),
        ]),
        ("dan-hockenmaier", "Dan Hockenmaier", "Marketplace growth loops", "https://youtu.be/CCC", [
            (0, 5, "marketplace liquidity supply demand growth loops"),
        ]),
    ]
    for slug, guest, title, url, chunks in data:
        ep = Episode(slug=slug, source_file=f"episodes/{slug}/transcript.md", guest=guest,
                     title=title, youtube_url=url, chunk_count=len(chunks), keywords=["growth"])
        db.add(ep)
        db.flush()
        for idx, start, text in chunks:
            db.add(Chunk(episode_id=ep.id, source_file=ep.source_file, chunk_index=idx, content=text,
                         start_seconds=start, embedding=fake_vector(text), embed_model=settings.embed_tag))
    db.commit()
    return data


@pytest.fixture
def session_id(client):
    return client.post("/sessions").json()["session_id"]
