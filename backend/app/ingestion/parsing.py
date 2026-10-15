"""Pure functions (no I/O, no DB, no network) so they are trivial to unit-test.

A transcript file looks like:

    ---                          <- YAML header: guest, title, youtube_url, ...
    guest: Ada Chen Rekhi
    ...
    ---
    # Title
    ## Transcript
    Ada Chen Rekhi (00:00:00):   <- speaker + timestamp
    Words words words...

    (00:01:21):                  <- timestamp-only paragraph (same speaker continues)
    More words...
"""

import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Optional

import yaml

FRONTMATTER_RE = re.compile(r"\A\ufeff?---\s*\n(.*?)\n---\s*\n", re.S)
TS_RE = re.compile(r"^[^\n]*?\((\d{1,2}):(\d{2}):(\d{2})\):")


@dataclass
class Paragraph:
    text: str
    start_seconds: Optional[int]  # most recent timestamp at or before this paragraph


@dataclass
class ChunkPiece:
    index: int
    text: str
    start_seconds: Optional[int]


def parse_frontmatter(raw: str) -> tuple[dict[str, Any], str]:
    """Return (metadata, body). Never raises: bad YAML => ({}, whole file)."""
    m = FRONTMATTER_RE.match(raw)
    if not m:
        return {}, raw.strip()
    try:
        meta = yaml.safe_load(m.group(1)) or {}
        if not isinstance(meta, dict):
            meta = {}
    except yaml.YAMLError:
        meta = {}
    return meta, raw[m.end():].strip()


def normalize_meta(meta: dict[str, Any], slug: str) -> dict[str, Any]:
    """Coerce header fields to clean types; tolerate missing ones (a few files lack some)."""
    pub = meta.get("publish_date")
    if isinstance(pub, datetime):
        pub = pub.date()
    elif isinstance(pub, str):
        try:
            pub = date.fromisoformat(pub[:10])
        except ValueError:
            pub = None
    elif not isinstance(pub, date):
        pub = None
    try:
        duration = int(float(meta.get("duration_seconds")))
    except (TypeError, ValueError):
        duration = None
    kws = meta.get("keywords")
    kws = [str(k) for k in kws] if isinstance(kws, list) else []
    title = " ".join(str(meta.get("title") or "").split()) or slug.replace("-", " ").title()
    guest = " ".join(str(meta.get("guest") or "").split()) or None
    return {
        "guest": guest, "title": title,
        "youtube_url": meta.get("youtube_url") or None,
        "video_id": meta.get("video_id") or None,
        "publish_date": pub, "duration_seconds": duration, "keywords": kws,
        "description": " ".join(str(meta.get("description") or "").split()) or None,
    }


def split_paragraphs(body: str) -> list[Paragraph]:
    """Split on blank lines, carrying the latest timestamp forward."""
    if "## Transcript" in body:
        body = body.split("## Transcript", 1)[1]
    paras: list[Paragraph] = []
    current: Optional[int] = None
    for block in re.split(r"\n\s*\n", body):
        text = block.strip()
        if not text:
            continue
        m = TS_RE.match(text)
        if m:
            h, mi, s = (int(x) for x in m.groups())
            current = h * 3600 + mi * 60 + s
        paras.append(Paragraph(text=text, start_seconds=current))
    return paras


def chunk_paragraphs(paras: list[Paragraph], size: int = 500, overlap: int = 50,
                     min_tail: int = 30) -> list[ChunkPiece]:
    """Greedy paragraph packing into ~`size`-word chunks with `overlap` words of
    context carried into the next chunk (so a sentence cut at a boundary is
    still seen whole by one of the two chunks). Words approximate tokens."""
    chunks: list[ChunkPiece] = []
    cur: list[str] = []
    cur_words = 0
    cur_start: Optional[int] = None

    def flush() -> None:
        nonlocal cur, cur_words, cur_start
        if not cur:
            return
        text = "\n\n".join(cur)
        chunks.append(ChunkPiece(len(chunks), text, cur_start))
        words = text.split()
        if overlap > 0 and len(words) > overlap:
            cur, cur_words = [" ".join(words[-overlap:])], overlap
        else:
            cur, cur_words = [], 0
        cur_start = None

    for para in paras:
        words = para.text.split()
        # an over-long paragraph (e.g. a sponsor read) is cut into word windows
        pieces = [para.text] if len(words) <= size else [
            " ".join(words[i:i + size]) for i in range(0, len(words), size)]
        for piece in pieces:
            n = len(piece.split())
            if cur_words + n > size and cur_words > overlap:
                flush()
            if cur_start is None:
                cur_start = para.start_seconds
            cur.append(piece)
            cur_words += n

    if cur and not (len(chunks) > 0 and cur_words <= overlap):  # drop pure-overlap remainder
        text = "\n\n".join(cur)
        if chunks and len(text.split()) < min_tail:
            prev = chunks[-1]
            chunks[-1] = ChunkPiece(prev.index, prev.text + "\n\n" + text, prev.start_seconds)
        else:
            chunks.append(ChunkPiece(len(chunks), text, cur_start))
    return chunks


def timestamp_url(youtube_url: Optional[str], start_seconds: Optional[int]) -> Optional[str]:
    """Deep link that opens the video at the chunk's moment."""
    if not youtube_url:
        return None
    if start_seconds is None:
        return youtube_url
    sep = "&" if "?" in youtube_url else "?"
    return f"{youtube_url}{sep}t={int(start_seconds)}s"


def format_timestamp(seconds: Optional[int]) -> Optional[str]:
    if seconds is None:
        return None
    h, rem = divmod(int(seconds), 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"
