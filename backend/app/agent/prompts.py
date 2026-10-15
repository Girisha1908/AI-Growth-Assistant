"""Shared prompt pieces. Prompts live in code, in one place, so a client engineer
can read and change them without hunting through routers."""

from typing import Optional

from app.agent.types import REFUSAL_MESSAGE

GROUNDING_RULES = f"""You are the Lenny Growth Assistant, built on transcripts of Lenny's Podcast.
RULES (non-negotiable):
1. Use ONLY facts found in the numbered transcript excerpts. Never use outside knowledge.
2. If the excerpts do not contain enough to answer, reply with exactly: {REFUSAL_MESSAGE}
3. Cite every claim with its excerpt number in square brackets, like [1] or [2][3]. Never invent a number, speaker, statistic or quote.
4. If you quote, quote verbatim and say who said it.
5. Be concise and concrete."""


def format_excerpts(chunks: list[dict], max_chars: int = 2600) -> str:
    """Number each excerpt; [n] in answers maps 1:1 to the sources list in the API."""
    blocks = []
    for n, c in enumerate(chunks, 1):
        who = c.get("guest") or "Unknown guest"
        title = c.get("title") or c["source_file"]
        ts = f" @ {c['timestamp']}" if c.get("timestamp") else ""
        body = c["content"].strip()
        if len(body) > max_chars:
            body = body[:max_chars].rsplit(" ", 1)[0] + " …"
        blocks.append(f"[{n}] {who} — {title}{ts}\n{body}")
    return "\n\n".join(blocks)


def learner_block(profile: Optional[dict]) -> str:
    """Optional personalisation. Only shapes HOW things are explained, never WHAT is true."""
    if not profile:
        return ""
    parts = []
    if profile.get("goal"):
        parts.append(f"Goal: {profile['goal']}")
    if profile.get("background"):
        parts.append(f"Background: {profile['background']}")
    if profile.get("known_concepts"):
        parts.append("Already understands: " + ", ".join(profile["known_concepts"]))
    if not parts:
        return ""
    return ("\n\nLEARNER CONTEXT (use only to choose analogies and level; facts must still "
            "come from the excerpts):\n" + "\n".join(parts))


def trim_history(history: list[dict], max_chars: int = 900) -> list[dict]:
    """Old assistant turns can be essays; clip them so they don't eat the context window."""
    out = []
    for m in history:
        content = m["content"]
        if len(content) > max_chars:
            content = content[:max_chars].rsplit(" ", 1)[0] + " …"
        out.append({"role": m["role"], "content": content})
    return out
