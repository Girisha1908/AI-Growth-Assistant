"""Claude (Anthropic) provider implementation for remote LLM inference."""

import asyncio
from typing import Optional
import requests

from app.config import settings
from app.providers.base import LLMProvider


class ClaudeProvider(LLMProvider):
    """LLM provider implementation for Anthropic's Claude Messages API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.2,
        timeout: int = 60,
    ):
        self.api_key = api_key or settings.ANTHROPIC_API_KEY
        if not self.api_key or not self.api_key.strip():
            raise ValueError(
                "Anthropic API key is not configured. Set ANTHROPIC_API_KEY in your environment or .env file."
            )

        self.model = model or getattr(settings, "CLAUDE_MODEL", "claude-3-5-sonnet-20241022")
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.timeout = timeout
        self.api_url = "https://api.anthropic.com/v1/messages"

    def _sync_chat(self, messages: list[dict]) -> str:
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        # Anthropic Messages API expects top-level 'system' parameter and alternating 'messages'
        system_prompts = []
        chat_messages = []

        for msg in messages:
            role = msg.get("role")
            content = msg.get("content", "")
            if role == "system":
                system_prompts.append(content)
            elif role in ("user", "assistant"):
                chat_messages.append({"role": role, "content": content})

        payload = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "messages": chat_messages,
        }
        if system_prompts:
            payload["system"] = "\n\n".join(system_prompts)

        try:
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
            content_blocks = data.get("content", [])
            text_blocks = [b.get("text", "") for b in content_blocks if b.get("type") == "text"]
            answer = "".join(text_blocks).strip()
            if not answer:
                raise RuntimeError("Empty response received from Claude API")
            return answer
        except requests.exceptions.ConnectionError as e:
            raise ConnectionError(
                f"Cannot connect to Anthropic API at {self.api_url} — check network connectivity."
            ) from e
        except requests.exceptions.Timeout as e:
            raise TimeoutError("Claude API request timed out") from e
        except requests.exceptions.HTTPError as e:
            raise RuntimeError(f"Claude API error {response.status_code}: {response.text}") from e
        except Exception as e:
            raise RuntimeError(f"Claude generation error: {e}") from e

    async def chat(self, messages: list[dict]) -> str:
        """Asynchronously invoke Anthropic's messages API in a worker thread."""
        return await asyncio.to_thread(self._sync_chat, messages)
