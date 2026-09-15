"""Transcript ingestion pipeline.

Run via: python -m app.scripts.ingest  (from the backend container)
Or:      docker compose exec api python -m app.scripts.ingest

This script:
1. Clones the Lenny's Podcast transcript repo (if not already present)
2. Walks all episode transcript markdown files
3. Chunks each transcript into ~500-token pieces with ~50-token overlap
4. Embeds each chunk using Ollama's nomic-embed-text model
5. Stores (source_file, chunk_index, content, embedding) in the chunks table

Idempotency: For each source file, existing chunks are deleted before
re-inserting. This means re-running the script produces a clean result
even if chunking logic changes — no silent duplicates.
"""

import argparse
import glob
import os
import subprocess
import sys
import time
from pathlib import Path

import requests
from sqlalchemy import text

from app.config import settings
from app.db import SessionLocal, engine, Base
from app.models import Chunk

# ── Constants ────────────────────────────────────────────────────────
TRANSCRIPT_REPO = "https://github.com/ChatPRD/lennys-podcast-transcripts.git"
TRANSCRIPTS_DIR = Path("/app/transcripts/source")
EPISODES_GLOB = "episodes/*/transcript.md"

# Chunking parameters (in approximate word/token counts)
CHUNK_SIZE = 500    # target tokens per chunk
CHUNK_OVERLAP = 50  # overlap tokens between consecutive chunks


def ensure_repo_cloned():
    """Clone the transcript repo if it doesn't exist or is empty."""
    if TRANSCRIPTS_DIR.exists() and any(TRANSCRIPTS_DIR.iterdir()):
        print(f"✓ Transcript repo already exists at {TRANSCRIPTS_DIR}")
        return

    print(f"Cloning transcript repo into {TRANSCRIPTS_DIR}...")
    TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ["git", "clone", "--depth", "1", TRANSCRIPT_REPO, str(TRANSCRIPTS_DIR)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"✗ git clone failed: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    print("✓ Transcript repo cloned successfully")


def parse_transcript(filepath: Path) -> str:
    """Parse a transcript markdown file into body text, stripping YAML frontmatter.

    Files use YAML frontmatter between --- delimiters, followed by the
    transcript content.
    """
    content = filepath.read_text(encoding="utf-8")
    parts = content.split("---", 2)

    if len(parts) >= 3:
        # parts[0] is empty (before first ---), parts[1] is frontmatter, parts[2] is body
        body = parts[2].strip()
    else:
        # No frontmatter, treat entire file as body
        body = content.strip()

    return body


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into chunks of approximately `chunk_size` tokens with `overlap`.

    Strategy: Split on paragraph boundaries (double newlines), then greedily
    combine paragraphs until we reach the token target. Uses word count as a
    rough token estimate (close enough for English text).
    """
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    if not paragraphs:
        return []

    chunks = []
    current_words = []
    current_count = 0

    for para in paragraphs:
        para_words = para.split()
        para_count = len(para_words)

        # If adding this paragraph exceeds the target and we already have content,
        # save the current chunk and start a new one with overlap
        if current_count + para_count > chunk_size and current_count > 0:
            chunks.append(" ".join(current_words))

            # Keep the last `overlap` words for context continuity
            if overlap > 0 and len(current_words) > overlap:
                current_words = current_words[-overlap:]
                current_count = len(current_words)
            else:
                current_words = []
                current_count = 0

        current_words.extend(para_words)
        current_count += para_count

    # Don't forget the last chunk
    if current_words:
        chunks.append(" ".join(current_words))

    return chunks


def get_embedding(text: str) -> list[float] | None:
    """Call Ollama's embedding API to get a vector for the given text.

    Returns None if the call fails (network error, Ollama not running, etc.).
    """
    url = f"{settings.OLLAMA_BASE_URL}/api/embed"
    try:
        response = requests.post(
            url,
            json={"model": settings.OLLAMA_EMBED_MODEL, "input": text},
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        embeddings = data.get("embeddings")
        if embeddings and len(embeddings) > 0:
            return embeddings[0]
        embedding = data.get("embedding")
        if embedding:
            return embedding
        print(f"  ⚠ Unexpected response format: {list(data.keys())}")
        return None
    except requests.exceptions.ConnectionError:
        print(f"  ✗ Cannot connect to Ollama at {url} — is it running?")
        return None
    except requests.exceptions.Timeout:
        print(f"  ✗ Ollama request timed out")
        return None
    except Exception as e:
        print(f"  ✗ Embedding error: {e}")
        return None


def ingest(limit: int | None = None, offset: int = 0, skip_existing: bool = False):
    """Main ingestion pipeline."""
    print("=" * 60)
    print("Lenny Growth Assistant — Transcript Ingestion")
    print("=" * 60)

    # Step 1: Ensure transcripts are available
    ensure_repo_cloned()

    # Enable pgvector extension (in case this runs before the API server)
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()

    # Ensure tables exist
    Base.metadata.create_all(bind=engine)

    # Step 2: Find all transcript files
    pattern = str(TRANSCRIPTS_DIR / EPISODES_GLOB)
    transcript_files = sorted(glob.glob(pattern))

    if not transcript_files:
        print(f"✗ No transcript files found matching {pattern}")
        print("  Check that the repo was cloned correctly.")
        sys.exit(1)

    total_available = len(transcript_files)
    if offset > 0:
        transcript_files = transcript_files[offset:]

    if limit is not None and limit > 0:
        transcript_files = transcript_files[:limit]
        print(f"\nFound {total_available} transcript files (processing {len(transcript_files)} files, offset={offset}, limit={limit})")
    else:
        print(f"\nFound {total_available} transcript files (processing {len(transcript_files)} files, offset={offset})")

    print(f"Embedding model: {settings.OLLAMA_EMBED_MODEL}")
    print(f"Ollama URL: {settings.OLLAMA_BASE_URL}")
    print()

    total_chunks = 0
    skipped_chunks = 0
    successful_episodes = 0
    failed_episodes = 0
    start_time = time.time()

    db = SessionLocal()
    try:
        for file_idx, filepath_str in enumerate(transcript_files, 1):
            filepath = Path(filepath_str)
            relative_path = str(filepath.relative_to(TRANSCRIPTS_DIR))

            try:
                # If skip_existing is enabled and chunks already exist, skip
                if skip_existing:
                    exists = db.query(Chunk.id).filter(Chunk.source_file == relative_path).first()
                    if exists:
                        print(f"  [{file_idx}/{len(transcript_files)}] {relative_path} — already in DB, skipping")
                        continue

                # Step 3: Parse and chunk
                body = parse_transcript(filepath)
                if not body:
                    print(f"  [{file_idx}/{len(transcript_files)}] {relative_path} — empty, skipping")
                    continue

                chunks = chunk_text(body)
                if not chunks:
                    print(f"  [{file_idx}/{len(transcript_files)}] {relative_path} — no chunks, skipping")
                    continue

                # Idempotency: delete existing chunks for this source file
                db.query(Chunk).filter(Chunk.source_file == relative_path).delete()
                db.flush()

                file_chunk_count = 0
                for chunk_idx, chunk_content in enumerate(chunks):
                    # Step 4: Embed
                    embedding = get_embedding(chunk_content)
                    if embedding is None:
                        skipped_chunks += 1
                        continue

                    # Step 5: Store
                    chunk = Chunk(
                        source_file=relative_path,
                        chunk_index=chunk_idx,
                        content=chunk_content,
                        embedding=embedding,
                    )
                    db.add(chunk)
                    file_chunk_count += 1

                db.commit()
                total_chunks += file_chunk_count
                successful_episodes += 1

            except Exception as file_err:
                db.rollback()
                failed_episodes += 1
                print(f"  ⚠ Error processing {relative_path}: {file_err}. Skipping file.", file=sys.stderr)
                continue

            # Step 6: Periodic progress logging (every 5 episodes or on final episode)
            if file_idx % 5 == 0 or file_idx == len(transcript_files):
                elapsed = time.time() - start_time
                print(
                    f"[Progress] Processed {file_idx}/{len(transcript_files)} episodes, "
                    f"{total_chunks} chunks stored so far (Elapsed: {elapsed:.0f}s)"
                )

    except KeyboardInterrupt:
        print("\n\n⚠ Interrupted! Committing progress so far...")
        db.commit()
    except Exception as e:
        print(f"\n✗ Fatal pipeline error: {e}")
        db.rollback()
        raise
    finally:
        db.close()

    elapsed = time.time() - start_time
    print()
    print("=" * 60)
    print(f"✓ Ingestion complete!")
    print(f"  Episodes requested:  {len(transcript_files)}")
    print(f"  Episodes succeeded:  {successful_episodes}")
    if failed_episodes > 0:
        print(f"  Episodes failed:     {failed_episodes} (skipped)")
    print(f"  Chunks stored:       {total_chunks}")
    print(f"  Chunks skipped:      {skipped_chunks} (embedding failures)")
    print(f"  Time elapsed:        {elapsed:.1f}s")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Ingest Lenny's Podcast transcripts into PostgreSQL with pgvector."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of episode transcripts to ingest (default: all, or INGEST_LIMIT env var).",
    )
    parser.add_argument(
        "--offset",
        type=int,
        default=0,
        help="Starting episode index offset (default: 0).",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip episodes that already have chunks stored in the database.",
    )
    args = parser.parse_args()

    limit = args.limit
    if limit is None and "INGEST_LIMIT" in os.environ:
        try:
            limit = int(os.environ["INGEST_LIMIT"])
        except ValueError:
            print(f"⚠ Invalid INGEST_LIMIT '{os.environ['INGEST_LIMIT']}', ignoring.", file=sys.stderr)

    ingest(limit=limit, offset=args.offset, skip_existing=args.skip_existing)


if __name__ == "__main__":
    main()


