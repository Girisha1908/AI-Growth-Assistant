"""Skill: PRD Architect -- draft a PRD for a product idea, backed by transcript evidence."""

from app.agent.artifacts import build_artifact, topic_title
from app.agent.prompts import GROUNDING_RULES, format_excerpts, learner_block
from app.agent.types import AgentContext, SkillOutput
from app.config import settings

NAME = "prd"

PRD_RULES = """OUTPUT FORMAT: ONE Markdown document inside a ```markdown fenced block and nothing else.
Title: '# PRD: <product idea>'. Sections in this order:
## Problem & user  ## Goals & success metrics  ## Scope (in / out)  ## Key flows
## Risks & trade-offs  ## Evidence from Lenny's Podcast (each point cites [n])  ## Open questions
Anything not supported by the excerpts must be labelled '(assumption)'. Never present an assumption as a guest's claim."""


async def run(ctx: AgentContext) -> SkillOutput:
    system = GROUNDING_RULES + "\n\n" + PRD_RULES + learner_block(ctx.profile)
    user = (f"Transcript excerpts:\n\n{format_excerpts(ctx.chunks)}\n\n"
            f"Product idea / request: {ctx.question}")
    raw = await ctx.provider.chat([{"role": "system", "content": system},
                                   {"role": "user", "content": user}])
    artifact = build_artifact(raw, "markdown", topic_title(ctx.question, "PRD: "),
                              settings.ARTIFACT_MAX_BYTES)
    return SkillOutput(
        answer=f"I drafted a PRD, “{artifact['title']}”, using {len(ctx.chunks)} transcript "
               f"excerpts as evidence. Open it in the viewer.",
        artifact=artifact, meta={"artifact_type": "markdown"})
