"""Ship 30 for 30 Content Generation Skill.

================================================================================
ENCODED SHIP 30 FOR 30 WRITING PRINCIPLES (Dickie Bush & Nicolas Cole)
================================================================================
1. The Hook (The Lead-In):
   - Opens with a punchy, 1-2 sentence declarative statement.
   - Answers three visceral reader questions immediately:
     * Who is this for?
     * What is this about?
     * Why should I care right now?
   - Creates an immediate open loop or thought-provoking contrast.

2. The "For WHO / SO THAT" Clarity Framework:
   - Explicitly establishes the target audience and the promised transformation.
   - Replaces vague platitudes with concrete outcomes.

3. High Rate of Revelation (RoR):
   - Fast information velocity with zero fluff. Every single sentence must introduce
     a new insight, tactic, or framework.
   - Eliminates filler words, passive preamble, and meta-commentary.

4. 1-3-1 Visual Rhythm:
   - Alternates sentence & paragraph lengths to create musical visual cadence:
     * 1: Short, punchy single-sentence opener.
     * 3: Three-sentence paragraph (or 3 bullet points) expanding the core argument.
     * 1: Punchy single-sentence closer or transition.
   - Avoids monotonic walls of text by utilizing intentional whitespace.

5. Skimmable Visual Architecture:
   - Clear, narrative-driven H2 and H3 subheadings that allow a reader to
     extract the full thesis in 30 seconds of skimming.
   - Bolding the first 2-4 words of key lines to anchor the reader's eye.
   - High-density bulleted or numbered frameworks for operational advice.

6. One Core Unifying Idea:
   - Every section serves a single, distinct thesis without topic drift.

7. Grounded Authority:
   - Backs claims directly with evidence, practitioner quotes, and specific
     mechanisms from Lenny's Podcast transcripts.

8. Actionable Takeaway / Conclusion:
   - Concludes with a concrete implementation heuristic, not an abstract summary.
================================================================================
"""

from typing import Optional
from app.config import get_llm_provider
from app.providers.base import LLMProvider

REFUSAL_MESSAGE = "I don't have enough information from the transcripts to answer that."


def build_ship30_prompt(topic: str, chunks: list[dict]) -> list[dict]:
    """Construct a grounded prompt strictly enforcing Ship 30 writing principles."""
    context_blocks = []
    for idx, c in enumerate(chunks, 1):
        context_blocks.append(
            f"--- [Snippet {idx} | Source: {c['source_file']} (chunk {c['chunk_index']})] ---\n"
            f"{c['content']}"
        )
    context_str = "\n\n".join(context_blocks)

    system_prompt = (
        "You are an expert ghostwriter and growth practitioner trained in the Ship 30 for 30 "
        "writing methodology (by Dickie Bush and Nicolas Cole). You write compelling, highly "
        "structured, actionable essays on startups, product management, and growth based exclusively "
        "on verified practitioner transcripts from Lenny's Podcast.\n\n"
        "CORE WRITING PRINCIPLES YOU MUST ENFORCE:\n"
        "1. THE HOOK: Begin with a punchy, 1-2 sentence declarative hook that creates curiosity.\n"
        "2. FOR WHO / SO THAT: Immediately clarify who this essay is for and what tangible result they will get.\n"
        "3. HIGH RATE OF REVELATION: High density of actionable insights with zero fluff or filler words.\n"
        "4. 1-3-1 RHYTHM: Structure points using the 1-3-1 cadence (1 punchy line, 3-sentence body or 3 bullets, 1 punchy conclusion).\n"
        "5. SKIMMABLE FORMATTING: Use descriptive markdown subheadings (## and ###), bold the first few words of key points, and use bullet lists.\n"
        "6. GROUNDED CLAIMS: Ground every insight in the provided podcast transcript context. Cite names, companies, and heuristics mentioned in the context.\n"
        "7. LENGTH TARGET: Produce an in-depth, thorough essay aiming for ~1,250 words (comprehensive multi-section deep dive).\n"
        "8. STRICT GROUNDING: If the provided transcript snippets do NOT contain enough information to cover this topic, "
        f"you MUST reply with: '{REFUSAL_MESSAGE}'"
    )

    user_prompt = (
        f"Transcript Context from Lenny's Podcast:\n\n{context_str}\n\n"
        f"Topic to write an essay on: {topic}\n\n"
        "Write a comprehensive, ~1,250-word Ship 30 style essay based strictly on the transcript context above."
    )

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


async def generate_ship30_essay(
    topic: str,
    chunks: list[dict],
    provider: Optional[LLMProvider] = None,
) -> tuple[str, Optional[str]]:
    """Generate a Ship 30 styled essay from retrieved podcast chunks.

    Returns a tuple of (essay_text, error_message).
    """
    messages = build_ship30_prompt(topic, chunks)
    llm = provider or get_llm_provider()

    try:
        essay = await llm.chat(messages)
        if not essay:
            return REFUSAL_MESSAGE, "Empty response from LLM"
        return essay, None
    except Exception as e:
        return REFUSAL_MESSAGE, str(e)
