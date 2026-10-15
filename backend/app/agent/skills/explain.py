"""Skill: explain simply, tailored to the learner profile."""

from app.agent.prompts import GROUNDING_RULES, format_excerpts, learner_block, trim_history
from app.agent.types import AgentContext, SkillOutput

NAME = "explain"

STYLE = """
STYLE FOR THIS ANSWER: explain to a smart beginner.
- Plain words; define any jargon in one short sentence.
- Give ONE analogy (tie it to what the learner already understands if known).
- Structure: **The idea** (2-3 sentences) → **Analogy** → **What the guests actually said** (with [n]) → **Key takeaway** (one line).
"""


async def run(ctx: AgentContext) -> SkillOutput:
    system = GROUNDING_RULES + STYLE + learner_block(ctx.profile)
    user = (f"Transcript excerpts:\n\n{format_excerpts(ctx.chunks)}\n\n"
            f"Explain simply: {ctx.question}")
    messages = [{"role": "system", "content": system},
                *trim_history(ctx.history), {"role": "user", "content": user}]
    return SkillOutput(answer=await ctx.provider.chat(messages))
