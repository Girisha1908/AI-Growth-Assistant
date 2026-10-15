"""Decide which skill handles a request.

Two ways in:
  1. The UI sends an explicit `mode` (the segmented control) -> we obey it.
  2. mode == "auto" (or omitted) -> cheap regex intent rules. No extra LLM call:
     a small local model is slow, and rules are deterministic and testable.
"""

import re
from typing import Optional

from app.agent.types import MODES, Route

_SHIP30 = re.compile(r"ship\s*-?30|atomic essay|\bessay\b", re.I)
_PRD = re.compile(r"\bprd\b|product requirements?( doc)?", re.I)
_QUIZ = re.compile(r"\bquiz\b|test me|flash ?cards?|practice questions", re.I)
_EXPLAIN = re.compile(r"\beli5\b|explain.{0,40}(simpl|like i|beginner|analogy)|in simple terms", re.I)
_ARTIFACT = re.compile(
    r"\b(create|make|generate|write|give me|build|draft|produce)\b.{0,50}"
    r"\b(markdown|html|document|doc|report|summary|one-?pager|cheat ?sheet|card|page|snippet)\b"
    r"|\b(markdown|html)\s+(summary|doc|document|card|page|snippet|report)\b", re.I)
_HTML_HINT = re.compile(r"\bhtml\b|\bcss\b|\bcard\b|\bpage\b|\bsnippet\b|\blanding\b", re.I)


def guess_artifact_type(message: str) -> str:
    return "html" if _HTML_HINT.search(message) else "markdown"


def decide_route(mode: Optional[str], message: str) -> Route:
    mode = (mode or "auto").lower().strip()
    if mode in MODES:
        art = guess_artifact_type(message) if mode == "artifact" else None
        return Route(mode, "explicit", art)
    if _SHIP30.search(message):
        return Route("ship30", "matched: ship 30 / essay")
    if _PRD.search(message):
        return Route("prd", "matched: PRD")
    if _QUIZ.search(message):
        return Route("quiz", "matched: quiz")
    if _EXPLAIN.search(message):
        return Route("explain", "matched: explain simply")
    if _ARTIFACT.search(message):
        return Route("artifact", "matched: artifact request", guess_artifact_type(message))
    return Route("ask", "default: grounded Q&A")
