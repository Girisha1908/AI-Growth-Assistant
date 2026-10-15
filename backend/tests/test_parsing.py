from datetime import date

from app.ingestion.parsing import (chunk_paragraphs, format_timestamp, normalize_meta,
                                   parse_frontmatter, split_paragraphs, timestamp_url)

RAW = """---
guest: Ada Chen Rekhi
title: Feeling stuck? | Ada
youtube_url: https://www.youtube.com/watch?v=abc
publish_date: 2023-04-21
duration_seconds: 230.0
keywords:
- growth
- roadmap
---

# Title

## Transcript

Ada Chen Rekhi (00:00:00):
First paragraph about careers.

Lenny (00:01:21):
Second paragraph.

(00:02:10):
Third paragraph continues.
"""


def test_frontmatter_and_meta():
    meta, body = parse_frontmatter(RAW)
    assert meta["guest"] == "Ada Chen Rekhi"
    m = normalize_meta(meta, "ada-chen-rekhi")
    assert m["publish_date"] == date(2023, 4, 21)
    assert m["duration_seconds"] == 230
    assert m["keywords"] == ["growth", "roadmap"]
    assert body.startswith("# Title")


def test_missing_fields_fall_back():
    m = normalize_meta({}, "some-guest-name")
    assert m["title"] == "Some Guest Name" and m["guest"] is None
    assert m["youtube_url"] is None and m["publish_date"] is None and m["keywords"] == []


def test_bad_yaml_does_not_raise():
    meta, body = parse_frontmatter("---\nkey: [unclosed\n---\nbody text")
    assert meta == {} and "body text" in body


def test_no_frontmatter():
    meta, body = parse_frontmatter("just text")
    assert meta == {} and body == "just text"


def test_timestamps_carry_forward():
    _, body = parse_frontmatter(RAW)
    paras = split_paragraphs(body)
    assert [p.start_seconds for p in paras] == [0, 81, 130]


def test_chunking_respects_size_overlap_and_start():
    words = lambda n, w: " ".join([w] * n)  # noqa: E731
    from app.ingestion.parsing import Paragraph
    paras = [Paragraph(f"Speaker ({i}:00:00):\n" + words(120, f"w{i}"), i * 100) for i in range(1, 9)]
    chunks = chunk_paragraphs(paras, size=300, overlap=20)
    assert len(chunks) >= 3
    assert [c.index for c in chunks] == list(range(len(chunks)))
    assert all(len(c.text.split()) <= 300 + 20 + 30 for c in chunks)
    assert chunks[0].start_seconds == 100
    # overlap: the tail of chunk 0 reappears at the start of chunk 1
    tail = chunks[0].text.split()[-5:]
    assert tail == chunks[1].text.split()[18:23] or " ".join(tail) in chunks[1].text


def test_oversized_paragraph_is_split():
    from app.ingestion.parsing import Paragraph
    chunks = chunk_paragraphs([Paragraph("word " * 1200, 0)], size=500, overlap=50)
    assert len(chunks) >= 3


def test_empty_body():
    assert chunk_paragraphs(split_paragraphs("")) == []


def test_deep_links():
    assert timestamp_url("https://www.youtube.com/watch?v=x", 248) == "https://www.youtube.com/watch?v=x&t=248s"
    assert timestamp_url("https://youtu.be/x", None) == "https://youtu.be/x"
    assert timestamp_url(None, 5) is None
    assert format_timestamp(3725) == "1:02:05" and format_timestamp(248) == "4:08"
