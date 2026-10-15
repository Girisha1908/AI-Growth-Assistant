"""Turn raw model output into a clean artifact. Pure functions, unit-tested.

Security note: this module does NOT make HTML safe. HTML is treated as
untrusted all the way to the browser, where it runs in a sandboxed iframe with
a strict CSP (see frontend/src/lib/sandbox.js and docs/architecture.md).
Here we only (1) strip the code fence the model wrapped it in, (2) make sure
HTML is a full document, (3) cap the size.
"""

import re
from typing import Optional

FENCE_RE = re.compile(r"```[ \t]*(markdown|md|html)?[ \t]*\n(.*?)```", re.S | re.I)
BASE_CSS = ("body{font-family:system-ui,-apple-system,Segoe UI,sans-serif;line-height:1.6;"
            "max-width:720px;margin:2rem auto;padding:0 1rem;color:#0f172a}")


def extract_fenced(text: str) -> str:
    """Return the content of the first code fence, or the whole text if unfenced."""
    m = FENCE_RE.search(text)
    if m:
        return m.group(2).strip()
    # an opening fence that was never closed (model hit the length limit)
    stripped = re.sub(r"^```[a-zA-Z]*\s*\n", "", text.strip())
    return stripped.strip()


def ensure_html_document(html: str, title: str = "Artifact") -> str:
    if re.search(r"<html[\s>]", html, re.I):
        return html
    return (f"<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
            f"<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
            f"<title>{title}</title><style>{BASE_CSS}</style></head><body>{html}</body></html>")


def derive_title(content: str, kind: str, fallback: str) -> str:
    if kind == "html":
        m = re.search(r"<title>(.*?)</title>", content, re.I | re.S)
        if m and m.group(1).strip():
            return " ".join(m.group(1).split())[:120]
        m = re.search(r"<h1[^>]*>(.*?)</h1>", content, re.I | re.S)
        if m:
            return re.sub(r"<[^>]+>", "", m.group(1)).strip()[:120] or fallback
        return fallback
    m = re.search(r"^\s*#\s+(.+)$", content, re.M)
    return (m.group(1).strip()[:120] if m else fallback)


def build_artifact(raw: str, kind: str, fallback_title: str, max_bytes: int) -> dict[str, str]:
    """kind: 'markdown' | 'html'. Raises ValueError if empty or too large."""
    content = extract_fenced(raw)
    if not content.strip():
        raise ValueError("Model returned no artifact content")
    title = derive_title(content, kind, fallback_title)
    if kind == "html":
        content = ensure_html_document(content, title)
    if len(content.encode("utf-8")) > max_bytes:
        raise ValueError(f"Artifact exceeds {max_bytes} bytes")
    return {"type": kind, "title": title, "content": content}


def topic_title(question: str, prefix: str = "") -> str:
    t = re.sub(r"\s+", " ", question).strip(" ?.!")
    t = t[:70] + ("…" if len(t) > 70 else "")
    return f"{prefix}{t}" if prefix else t


def word_count(text: str) -> int:
    return len(re.findall(r"\b[\w'’-]+\b", text))
