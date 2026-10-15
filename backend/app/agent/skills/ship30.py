"""Ship 30 for 30 content skill.

================================================================================
ENCODED SHIP 30 FOR 30 WRITING PRINCIPLES (Dickie Bush & Nicolas Cole)
================================================================================
1. The Hook: a punchy 1-2 sentence opener that tells the reader who this is for,
   what it is about, and why they should care now. Creates an open loop.
2. "For WHO / SO THAT" clarity: name the audience and the promised transformation.
3. High Rate of Revelation: every sentence adds a new insight, tactic or framework.
   No filler, no preamble, no meta-commentary.
4. 1-3-1 Visual Rhythm: alternate one punchy line, a three-sentence (or 3-bullet)
   expansion, and a one-line closer. No walls of text.
5. Skimmable Architecture: narrative H2 headings that tell the story on their own;
   **bold** the first few words of key lines; bullets for frameworks.
6. One Core Idea: every section serves a single thesis; no topic drift.
7. Grounded Authority: claims backed by practitioner evidence from the transcripts,
   cited [n]. (Our addition: this is a RAG product.)
8. Actionable Takeaway: finish with a concrete heuristic the reader can apply today.
================================================================================

Why two strategies?
  single    one long generation. Simple, but small local models stop at ~600 words.
  sectioned outline first, then one short call per section (hook, 4 body sections,
            takeaway). Each call is easy for a 3B model, and the sum reaches the
            ~1,250-word target. Falls back to `single` if the outline cannot be parsed.
"""

import re

from app.agent.artifacts import word_count
from app.agent.prompts import GROUNDING_RULES, format_excerpts, learner_block
from app.agent.types import AgentContext, SkillOutput

NAME = "ship30"

PRINCIPLES_PROMPT = """WRITE IN SHIP 30 FOR 30 STYLE:
- Short paragraphs (1-3 sentences). Plain, vivid, specific language.
- 1-3-1 rhythm: a one-line punch, a three-sentence (or 3-bullet) expansion, a one-line closer.
- Every sentence earns its place (high rate of revelation). No filler or meta talk.
- **Bold** the first few words of key lines. Use bullets for frameworks.
- Back claims with the excerpts and cite them [n]. Do not invent facts or quotes."""

OUTLINE_PROMPT = """Plan a Ship 30 for 30 essay about the topic, using ONLY the excerpts.
Reply in exactly this format and nothing else:
Title: <a specific, curiosity-driven title>
1. <section heading>
2. <section heading>
3. <section heading>
4. <section heading>
Headings must be narrative (they should tell the story if read alone) and each must be supported by the excerpts."""


def parse_outline(text: str) -> tuple[str, list[str]]:
    title = ""
    headings: list[str] = []
    for line in text.splitlines():
        clean = line.strip()
        if not clean:
            continue
        if not title and re.match(r"(?i)^\W*title\s*:", clean):
            title = re.sub(r"(?i)^\W*title\s*:\s*", "", clean)
            continue
        m = re.match(r"^\s*(?:\d+[.)]|[-*•])\s+(.+)$", clean)
        if m:
            headings.append(m.group(1))
    strip = lambda s: re.sub(r"[*_`#\"“”]", "", s).strip()  # noqa: E731
    return strip(title), [h for h in (strip(h) for h in headings) if h][:4]


def _system(ctx: AgentContext) -> str:
    return GROUNDING_RULES + "\n\n" + PRINCIPLES_PROMPT + learner_block(ctx.profile)


async def _single(ctx: AgentContext) -> SkillOutput:
    user = (f"Transcript excerpts:\n\n{format_excerpts(ctx.chunks)}\n\n"
            f"Write a Ship 30 for 30 essay of about {ctx.target_words} words on: {ctx.question}\n"
            "Structure: '# Title', a hook, 4 sections with '##' headings, then '## Takeaway'.")
    text = (await ctx.provider.chat([{"role": "system", "content": _system(ctx)},
                                     {"role": "user", "content": user}])).strip()
    title = (re.search(r"^#\s+(.+)$", text, re.M) or [None, ctx.question[:80]])[1]
    return _output(title, text, ctx, strategy="single", calls=1)


async def _sectioned(ctx: AgentContext) -> SkillOutput | None:
    excerpts = format_excerpts(ctx.chunks)
    outline = await ctx.provider.chat([
        {"role": "system", "content": _system(ctx) + "\n\n" + OUTLINE_PROMPT},
        {"role": "user", "content": f"Excerpts:\n\n{excerpts}\n\nTopic: {ctx.question}"}])
    title, headings = parse_outline(outline)
    if len(headings) < 3:
        return None  # outline unusable -> caller falls back to `single`
    title = title or ctx.question[:80]
    calls = 1

    async def write(label: str, instruction: str, words: int) -> str:
        nonlocal calls
        calls += 1
        user = (f"Excerpts:\n\n{excerpts}\n\nEssay title: {title}\n"
                f"Section plan: {' | '.join(headings)}\n\n"
                f"Write ONLY the '{label}' part (~{words} words). {instruction} "
                "Do not repeat other sections. Do not include a heading line.")
        return (await ctx.provider.chat([{"role": "system", "content": _system(ctx)},
                                         {"role": "user", "content": user}])).strip()

    total = ctx.target_words
    hook_w, take_w = int(total * 0.12), int(total * 0.10)
    body_w = int((total - hook_w - take_w) / len(headings))
    parts = [f"# {title}", await write(
        "Hook", "Open with a punchy 1-2 sentence hook (who it's for, what it's about, why now), "
                "then 2-3 short lines that set up the story.", hook_w)]
    for h in headings:
        body = await write(f"section titled '{h}'",
                           "Use the 1-3-1 rhythm, bold key phrases, cite [n].", body_w)
        parts.append(f"## {h}\n\n{body}")
    parts.append("## Takeaway\n\n" + await write(
        "Takeaway", "Give ONE specific, actionable heuristic the reader can apply today.", take_w))
    return _output(title, "\n\n".join(parts), ctx, strategy="sectioned", calls=calls)


def _output(title: str, essay: str, ctx: AgentContext, strategy: str, calls: int) -> SkillOutput:
    words = word_count(essay)
    return SkillOutput(
        answer=(f"I wrote a Ship 30 for 30 essay, “{title}” (~{words} words), grounded in "
                f"{len(ctx.chunks)} transcript excerpts. Open it in the viewer."),
        artifact={"type": "markdown", "title": title, "content": essay},
        meta={"word_count": words, "target_words": ctx.target_words,
              "strategy": strategy, "llm_calls": calls})


async def run(ctx: AgentContext) -> SkillOutput:
    if ctx.strategy == "sectioned":
        result = await _sectioned(ctx)
        if result is not None:
            return result
    return await _single(ctx)
