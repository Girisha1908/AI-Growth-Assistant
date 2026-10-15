"""The user's existing database (first version of the app) must upgrade in place,
keeping its already-embedded chunks."""

import sqlalchemy as sa

from app.migrate import init_db
from tests.conftest import ADMIN_URL, fake_vector

LEGACY_DB = "lenny_legacy"


def test_legacy_schema_upgrades_in_place():
    admin = sa.create_engine(ADMIN_URL, isolation_level="AUTOCOMMIT")
    with admin.connect() as c:
        c.execute(sa.text(f'DROP DATABASE IF EXISTS "{LEGACY_DB}"'))
        c.execute(sa.text(f'CREATE DATABASE "{LEGACY_DB}"'))
    url = ADMIN_URL.rsplit("/", 1)[0] + f"/{LEGACY_DB}"
    eng = sa.create_engine(url)
    vec = "[" + ",".join(str(x) for x in fake_vector("legacy chunk text")) + "]"
    with eng.begin() as c:   # the v1 schema, exactly as the first build created it
        c.execute(sa.text("CREATE EXTENSION vector"))
        c.execute(sa.text("CREATE TABLE sessions (id uuid PRIMARY KEY, created_at timestamptz DEFAULT now() NOT NULL, metadata json)"))
        c.execute(sa.text("CREATE TABLE messages (id uuid PRIMARY KEY, session_id uuid REFERENCES sessions(id) ON DELETE CASCADE, role varchar(50) NOT NULL, content text NOT NULL, created_at timestamptz DEFAULT now() NOT NULL)"))
        c.execute(sa.text("CREATE TABLE chunks (id uuid PRIMARY KEY, source_file varchar(500) NOT NULL, chunk_index integer NOT NULL, content text NOT NULL, embedding vector(768) NOT NULL, created_at timestamptz DEFAULT now() NOT NULL, CONSTRAINT uq_chunk_source_index UNIQUE (source_file, chunk_index))"))
        c.execute(sa.text("INSERT INTO chunks (id, source_file, chunk_index, content, embedding) VALUES (gen_random_uuid(), 'episodes/x/transcript.md', 0, 'legacy chunk text', CAST(:v AS vector))"), {"v": vec})

    init_db(eng)
    init_db(eng)   # idempotent: second run must be a no-op

    with eng.connect() as c:
        cols = {r[0] for r in c.execute(sa.text("SELECT column_name FROM information_schema.columns WHERE table_name='chunks'"))}
        assert {"episode_id", "start_seconds", "embed_model", "tsv"} <= cols
        mcols = {r[0] for r in c.execute(sa.text("SELECT column_name FROM information_schema.columns WHERE table_name='messages'"))}
        assert {"mode", "sources", "artifact", "meta"} <= mcols
        assert c.execute(sa.text("SELECT count(*) FROM chunks")).scalar() == 1      # data preserved
        # the generated tsvector column was back-filled for the legacy row
        assert c.execute(sa.text("SELECT count(*) FROM chunks WHERE tsv @@ to_tsquery('english','legacy')")).scalar() == 1
        idx = {r[0] for r in c.execute(sa.text("SELECT indexname FROM pg_indexes WHERE tablename='chunks'"))}
        assert {"ix_chunks_tsv", "ix_chunks_embedding_hnsw"} <= idx
    eng.dispose()
