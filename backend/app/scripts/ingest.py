"""Transcript ingestion pipeline.

    docker compose exec api python -m app.scripts.ingest              # everything (resumable)
    docker compose exec api python -m app.scripts.ingest --limit 20   # a slice
    docker compose exec api python -m app.scripts.ingest --dry-run    # parse+chunk only, no Ollama
    docker compose exec api python -m app.scripts.ingest --force      # re-embed everything

Per episode (atomic -- all chunks or none):
  1. parse YAML header  -> `episodes` row (guest, title, YouTube URL, date, ...)
  2. split into chunks  -> ~500 words, 50 overlap, with the timestamp of each chunk
  3. embed in batches   -> Ollama /api/embed
  4. replace the episode's chunks in one transaction (so re-runs never duplicate)

Resumable: an episode whose chunks were already embedded with the CURRENT
embedding setup is skipped, so you can stop (Ctrl+C) and re-run any time.
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path

from sqlalchemy import func

from app.config import settings
from app.db import SessionLocal, engine
from app.embeddings import EmbeddingError, embed_documents
from app.ingestion.parsing import (chunk_paragraphs, normalize_meta, parse_frontmatter,
                                   split_paragraphs)
from app.migrate import init_db
from app.models import Chunk, Episode

TRANSCRIPT_REPO = "https://github.com/ChatPRD/lennys-podcast-transcripts.git"


def ensure_repo(path: Path) -> None:
    if path.exists() and any(path.iterdir()):
        print(f"✓ Transcript repo found at {path}")
        return
    print(f"Cloning transcript repo into {path} ...")
    path.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(["git", "clone", "--depth", "1", TRANSCRIPT_REPO, str(path)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print(f"✗ git clone failed: {r.stderr}", file=sys.stderr)
        sys.exit(1)
    print("✓ Cloned")


def prepare_episode(file: Path, root: Path) -> dict:
    """Parse + chunk one transcript. Pure CPU work; no DB, no network."""
    slug = file.parent.name
    meta, body = parse_frontmatter(file.read_text(encoding="utf-8"))
    pieces = chunk_paragraphs(split_paragraphs(body), settings.CHUNK_WORDS,
                              settings.CHUNK_OVERLAP_WORDS)
    return {"slug": slug, "source_file": file.relative_to(root).as_posix(),
            "meta": normalize_meta(meta, slug), "pieces": pieces}


def is_up_to_date(db, source_file: str) -> bool:
    ep = db.query(Episode).filter(Episode.source_file == source_file).first()
    if not ep or ep.chunk_count == 0:
        return False
    stale = (db.query(func.count(Chunk.id))
             .filter(Chunk.source_file == source_file,
                     (Chunk.embed_model.is_(None)) | (Chunk.embed_model != settings.embed_tag))
             .scalar())
    return stale == 0


def store_episode(db, prepared: dict, vectors: list[list[float]]) -> None:
    """Replace an episode's chunks atomically."""
    db.query(Chunk).filter(Chunk.source_file == prepared["source_file"]).delete()
    ep = db.query(Episode).filter(Episode.slug == prepared["slug"]).first()
    if ep is None:
        ep = Episode(slug=prepared["slug"], source_file=prepared["source_file"],
                     title=prepared["meta"]["title"])
        db.add(ep)
    for k, v in prepared["meta"].items():
        setattr(ep, k, v)
    ep.source_file = prepared["source_file"]
    db.flush()
    for piece, vec in zip(prepared["pieces"], vectors):
        db.add(Chunk(episode_id=ep.id, source_file=prepared["source_file"],
                     chunk_index=piece.index, content=piece.text,
                     start_seconds=piece.start_seconds, embedding=vec,
                     embed_model=settings.embed_tag))
    ep.chunk_count = len(prepared["pieces"])
    db.commit()


def run(path: str, limit, offset: int, force: bool, dry_run: bool) -> int:
    root = Path(path)
    print("=" * 64 + "\nLenny Growth Assistant — transcript ingestion\n" + "=" * 64)
    ensure_repo(root)
    files = sorted(root.glob("episodes/*/transcript.md"))
    if not files:
        print(f"✗ No transcripts under {root}/episodes/*/transcript.md", file=sys.stderr)
        return 1
    total = len(files)
    files = files[offset:]
    if limit:
        files = files[:limit]
    print(f"Episodes available: {total} | this run: {len(files)} (offset={offset}, limit={limit})")
    print(f"Embedding: {settings.embed_tag} via {settings.OLLAMA_BASE_URL} "
          f"(batch={settings.EMBED_BATCH_SIZE}){'  [DRY RUN]' if dry_run else ''}\n")

    if not dry_run:
        init_db(engine)
        try:
            embed_documents(["connectivity check"])
        except EmbeddingError as e:
            print(f"✗ {e}\n  Start Ollama and run: ollama pull {settings.OLLAMA_EMBED_MODEL}",
                  file=sys.stderr)
            return 2

    stats = {"done": 0, "skipped": 0, "failed": 0, "chunks": 0}
    start = time.time()
    db = SessionLocal()
    try:
        for i, file in enumerate(files, 1):
            prepared = prepare_episode(file, root)
            n = len(prepared["pieces"])
            if dry_run:
                stats["done"] += 1
                stats["chunks"] += n
                if i <= 3:
                    print(f"  {prepared['slug']}: {n} chunks | {prepared['meta']['guest']}")
                continue
            if not force and is_up_to_date(db, prepared["source_file"]):
                stats["skipped"] += 1
                continue
            try:
                vectors = embed_documents([p.text for p in prepared["pieces"]])
                store_episode(db, prepared, vectors)
                stats["done"] += 1
                stats["chunks"] += n
            except Exception as e:  # noqa: BLE001 - one bad episode must not stop the run
                db.rollback()
                stats["failed"] += 1
                print(f"  ✗ {prepared['slug']}: {e}", file=sys.stderr)
            if i % 5 == 0 or i == len(files):
                elapsed = time.time() - start
                working = stats["done"] + stats["failed"]
                eta = (elapsed / working) * (len(files) - i) if working else 0
                print(f"[{i}/{len(files)}] done={stats['done']} skipped={stats['skipped']} "
                      f"failed={stats['failed']} chunks={stats['chunks']} "
                      f"elapsed={elapsed:.0f}s eta≈{eta/60:.0f}min", flush=True)
    except KeyboardInterrupt:
        print("\nInterrupted — safe to re-run; finished episodes are kept.")
    finally:
        db.close()

    print("\n" + "=" * 64)
    print(f"Done: {stats['done']} | skipped (up to date): {stats['skipped']} | "
          f"failed: {stats['failed']} | chunks written: {stats['chunks']}")
    print("Check: curl http://localhost:8000/health/chunks")
    return 0 if stats["failed"] == 0 else 3


def main() -> None:
    ap = argparse.ArgumentParser(description="Ingest Lenny's Podcast transcripts")
    ap.add_argument("--path", default=settings.TRANSCRIPTS_DIR, help="transcript repo directory")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--offset", type=int, default=0)
    ap.add_argument("--force", action="store_true", help="re-embed even if up to date")
    ap.add_argument("--dry-run", action="store_true", help="parse and chunk only (no Ollama/DB)")
    a = ap.parse_args()
    sys.exit(run(a.path, a.limit, a.offset, a.force, a.dry_run))


if __name__ == "__main__":
    main()
