"""Skill: grounded Q&A (the default)."""

from app.agent.prompts import GROUNDING_RULES, format_excerpts, trim_history
from app.agent.types import AgentContext, SkillOutput

NAME = "ask"


async def run(ctx: AgentContext) -> SkillOutput:
    user = (f"Transcript excerpts:\n\n{format_excerpts(ctx.chunks)}\n\n"
            f"Question: {ctx.question}\n\nAnswer using only the excerpts, with [n] citations.")
    messages = [{"role": "system", "content": GROUNDING_RULES},
                *trim_history(ctx.history), {"role": "user", "content": user}]
    return SkillOutput(answer=await ctx.provider.chat(messages))
