"""Skill: Quiz me -- active recall questions built only from retrieved excerpts."""

from app.agent.artifacts import build_artifact, topic_title
from app.agent.prompts import GROUNDING_RULES, format_excerpts, learner_block
from app.agent.types import AgentContext, SkillOutput
from app.config import settings

NAME = "quiz"

QUIZ_RULES = """OUTPUT FORMAT: ONE Markdown document inside a ```markdown fenced block and nothing else.
Title: '# Quiz: <topic>'. Write exactly 5 questions: 3 multiple-choice (A-D) and 2 short-answer.
Every question must be answerable from the excerpts alone. After EACH question put its answer in a collapsible block:

<details><summary>Show answer</summary>

**Answer:** ... [n]

</details>"""


async def run(ctx: AgentContext) -> SkillOutput:
    system = GROUNDING_RULES + "\n\n" + QUIZ_RULES + learner_block(ctx.profile)
    user = (f"Transcript excerpts:\n\n{format_excerpts(ctx.chunks)}\n\n"
            f"Quiz topic: {ctx.question}")
    raw = await ctx.provider.chat([{"role": "system", "content": system},
                                   {"role": "user", "content": user}])
    artifact = build_artifact(raw, "markdown", topic_title(ctx.question, "Quiz: "),
                              settings.ARTIFACT_MAX_BYTES)
    return SkillOutput(
        answer="Here's a 5-question quiz built from the transcripts. Try answering before you open each answer.",
        artifact=artifact, meta={"artifact_type": "markdown"})
