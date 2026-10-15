"""Claude via the Anthropic **Claude Agent SDK** (the agent layer named in the brief).

Why it is a *provider* and not the whole agent layer: the Agent SDK drives
Claude only, but the demo must also run on local Ollama. So routing, skills and
retrieval live in `app.agent` (provider-agnostic), and this class lets the same
agent run on Claude's agent runtime when LLM_PROVIDER=claude-agent.

Tools are disabled on purpose: retrieval is done by OUR code so citations come
from real database rows, never from model output.

STATUS: written against claude-agent-sdk 0.2.x signatures; NOT exercised
end-to-end (needs a paid ANTHROPIC_API_KEY). Treat as unverified.
"""

from typing import Optional

from app.config import settings
from app.providers.base import LLMProvider


class ClaudeAgentProvider(LLMProvider):
    name = "claude-agent"

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.ANTHROPIC_API_KEY
        if not self.api_key or not self.api_key.strip():
            raise ValueError(
                "Anthropic API key is not configured. Set ANTHROPIC_API_KEY in .env, "
                "or switch to the local Ollama provider.")
        self.model = model or settings.CLAUDE_MODEL

    async def chat(self, messages: list[dict]) -> str:
        try:
            from claude_agent_sdk import (AssistantMessage, ClaudeAgentOptions, CLINotFoundError,
                                          ResultMessage, TextBlock, query)
        except ImportError as e:  # pragma: no cover
            raise RuntimeError("claude-agent-sdk is not installed") from e

        system = "\n\n".join(m["content"] for m in messages if m["role"] == "system")
        convo = "\n\n".join(f"{m['role'].upper()}: {m['content']}"
                            for m in messages if m["role"] != "system")
        options = ClaudeAgentOptions(
            system_prompt=system or None, model=self.model, max_turns=1, tools=[],
            setting_sources=[], env={"ANTHROPIC_API_KEY": self.api_key},
        )
        parts: list[str] = []
        try:
            async for msg in query(prompt=convo, options=options):
                if isinstance(msg, AssistantMessage):
                    parts.extend(b.text for b in msg.content if isinstance(b, TextBlock))
                elif isinstance(msg, ResultMessage) and msg.is_error:
                    raise RuntimeError(f"Claude agent error: {msg.result or msg.errors}")
        except CLINotFoundError as e:
            raise ConnectionError("Claude Code runtime not found for the Agent SDK") from e
        text = "".join(parts).strip()
        if not text:
            raise RuntimeError("Empty response from Claude Agent SDK")
        return text

    async def ping(self) -> dict:
        return {"reachable": True, "note": "not probed (avoids spending tokens)"}
