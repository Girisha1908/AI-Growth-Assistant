"""Skill: generate a Markdown document or a self-contained HTML snippet."""

from app.agent.artifacts import build_artifact, topic_title
from app.agent.prompts import GROUNDING_RULES, format_excerpts, learner_block
from app.agent.types import AgentContext, SkillOutput
from app.config import settings

NAME = "artifact"

MARKDOWN_RULES = """OUTPUT FORMAT: reply with ONE Markdown document inside a ```markdown fenced block and nothing else.
Start with a single '# Title'. Use '##' headings, short bullets, and [n] citations. End with a '## Sources' list naming guest and episode."""

HTML_RULES = """OUTPUT FORMAT: reply with ONE complete, self-contained HTML document inside a ```html fenced block and nothing else.
Hard constraints: inline <style> only; NO JavaScript, NO <script>, NO external URLs, NO images, NO forms. Use semantic HTML, readable typography, and a clean card layout. Include [n] citation markers as plain text and a small 'Sources' footer."""


async def run(ctx: AgentContext) -> SkillOutput:
    kind = ctx.artifact_type if ctx.artifact_type in ("markdown", "html") else "markdown"
    system = GROUNDING_RULES + "\n\n" + (HTML_RULES if kind == "html" else MARKDOWN_RULES) \
        + learner_block(ctx.profile)
    user = (f"Transcript excerpts:\n\n{format_excerpts(ctx.chunks)}\n\n"
            f"Request: {ctx.question}\n\nCreate the {kind} artifact now, grounded only in the excerpts.")
    raw = await ctx.provider.chat([{"role": "system", "content": system},
                                   {"role": "user", "content": user}])
    artifact = build_artifact(raw, kind, topic_title(ctx.question), settings.ARTIFACT_MAX_BYTES)
    label = "HTML page" if kind == "html" else "Markdown document"
    return SkillOutput(
        answer=f"I created a {label}, “{artifact['title']}”, grounded in {len(ctx.chunks)} "
               f"transcript excerpts. Open it in the viewer.",
        artifact=artifact, meta={"artifact_type": kind})
