"""Tiny idempotent schema upgrader (Postgres only).

`Base.metadata.create_all` creates MISSING tables but never alters existing
ones. Users who ran an earlier version already have `chunks` and `messages`, so
we add the new columns/indexes.

Important detail: `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` takes an ACCESS
EXCLUSIVE lock EVEN WHEN the column already exists. Running that on every
startup would block behind any open transaction (found by a hanging test), so we
first look in the catalog (no lock) and only issue DDL that is really needed,
with a lock_timeout so a stuck lock fails loudly instead of hanging forever.

(Alembic is the production answer; see docs/architecture.md.)
"""

from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine

from app.db import Base
from app.logging_utils import get_logger

log = get_logger("migrate")

# (kind, table, name, sql)
MIGRATIONS = [
    # chunks: link to episode, timestamp, embedding provenance
    ("column", "chunks", "episode_id",
     "ALTER TABLE chunks ADD COLUMN episode_id uuid REFERENCES episodes(id) ON DELETE CASCADE"),
    ("column", "chunks", "start_seconds", "ALTER TABLE chunks ADD COLUMN start_seconds integer"),
    ("column", "chunks", "embed_model", "ALTER TABLE chunks ADD COLUMN embed_model varchar(100)"),
    ("index", "chunks", "ix_chunks_episode_id", "CREATE INDEX ix_chunks_episode_id ON chunks (episode_id)"),
    # messages: what the assistant attached to its answer
    ("column", "messages", "mode", "ALTER TABLE messages ADD COLUMN mode varchar(30)"),
    ("column", "messages", "sources", "ALTER TABLE messages ADD COLUMN sources json"),
    ("column", "messages", "artifact", "ALTER TABLE messages ADD COLUMN artifact json"),
    ("column", "messages", "meta", "ALTER TABLE messages ADD COLUMN meta json"),
    # keyword search: generated tsvector + GIN index (the keyword half of hybrid search)
    ("column", "chunks", "tsv",
     "ALTER TABLE chunks ADD COLUMN tsv tsvector GENERATED ALWAYS AS (to_tsvector('english', content)) STORED"),
    ("index", "chunks", "ix_chunks_tsv", "CREATE INDEX ix_chunks_tsv ON chunks USING GIN (tsv)"),
    # vector index: HNSW keeps cosine search fast at 12k+ chunks
    ("index", "chunks", "ix_chunks_embedding_hnsw",
     "CREATE INDEX ix_chunks_embedding_hnsw ON chunks USING hnsw (embedding vector_cosine_ops)"),
]


def _exists(conn: Connection, kind: str, table: str, name: str) -> bool:
    if kind == "column":
        sql = ("SELECT 1 FROM information_schema.columns WHERE table_schema = current_schema() "
               "AND table_name = :t AND column_name = :n")
    else:
        sql = "SELECT 1 FROM pg_indexes WHERE schemaname = current_schema() AND indexname = :n"
    return conn.execute(text(sql), {"t": table, "n": name}).first() is not None


def init_db(engine: Engine) -> None:
    if engine.dialect.name != "postgresql":
        Base.metadata.create_all(bind=engine)
        return
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.create_all(bind=engine)
    applied = []
    for kind, table, name, sql in MIGRATIONS:
        with engine.begin() as conn:
            if _exists(conn, kind, table, name):
                continue
            conn.execute(text("SET LOCAL lock_timeout = '15s'"))
            conn.execute(text(sql))
            applied.append(name)
    log.info("schema_ready", extra={"applied": applied})
