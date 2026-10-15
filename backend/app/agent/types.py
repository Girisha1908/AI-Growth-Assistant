from dataclasses import dataclass, field
from typing import Any, Optional

from app.providers.base import LLMProvider

REFUSAL_MESSAGE = "I don't have enough information from the transcripts to answer that."
MODES = ("ask", "explain", "quiz", "ship30", "artifact", "prd")


@dataclass
class Route:
    mode: str
    reason: str
    artifact_type: Optional[str] = None  # "markdown" | "html" (artifact mode only)


@dataclass
class AgentContext:
    question: str
    chunks: list[dict[str, Any]]
    history: list[dict[str, str]]            # prior turns: [{'role','content'}]
    provider: LLMProvider
    profile: Optional[dict[str, Any]] = None  # learner profile, if personalising
    artifact_type: Optional[str] = None
    target_words: int = 1250
    strategy: str = "sectioned"


@dataclass
class SkillOutput:
    answer: str
    artifact: Optional[dict[str, str]] = None  # {type,title,content}
    meta: dict[str, Any] = field(default_factory=dict)
