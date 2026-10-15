"""Anthropic Messages API provider (cloud path, plain HTTP).

Verified at code level only unless an ANTHROPIC_API_KEY is supplied; see
docs/architecture.md ("Model provider toggle").
"""

import asyncio
from typing import Optional

import requests

from app.config import settings
from app.providers.base import LLMProvider


class ClaudeProvider(LLMProvider):
    name = "claude"

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None,
                 max_tokens: int = 2048, temperature: float = 0.2, timeout: int = 120):
        self.api_key = api_key or settings.ANTHROPIC_API_KEY
        if not self.api_key or not self.api_key.strip():
            raise ValueError(
                "Anthropic API key is not configured. Set ANTHROPIC_API_KEY in .env, "
                "or switch to the local Ollama provider.")
        self.model = model or settings.CLAUDE_MODEL
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.timeout = timeout
        self.api_url = "https://api.anthropic.com/v1/messages"

    def _sync_chat(self, messages: list[dict]) -> str:
        headers = {"x-api-key": self.api_key, "anthropic-version": "2023-06-01",
                   "content-type": "application/json"}
        system_parts, chat_messages = [], []
        for msg in messages:
            role, content = msg.get("role"), msg.get("content", "")
            if role == "system":
                system_parts.append(content)
            elif role in ("user", "assistant"):
                chat_messages.append({"role": role, "content": content})
        payload = {"model": self.model, "max_tokens": self.max_tokens,
                   "temperature": self.temperature, "messages": chat_messages}
        if system_parts:
            payload["system"] = "\n\n".join(system_parts)
        try:
            response = requests.post(self.api_url, headers=headers, json=payload,
                                     timeout=self.timeout)
            response.raise_for_status()
            blocks = response.json().get("content", [])
            answer = "".join(b.get("text", "") for b in blocks if b.get("type") == "text").strip()
            if not answer:
                raise RuntimeError("Empty response received from Claude API")
            return answer
        except requests.exceptions.ConnectionError as e:
            raise ConnectionError("Cannot reach api.anthropic.com. Check your network.") from e
        except requests.exceptions.Timeout as e:
            raise TimeoutError("Claude API request timed out") from e
        except requests.exceptions.HTTPError as e:
            raise RuntimeError(f"Claude API error {response.status_code}: {response.text[:300]}") from e
        except RuntimeError:
            raise
        except Exception as e:  # noqa: BLE001
            raise RuntimeError(f"Claude generation error: {e}") from e

    async def chat(self, messages: list[dict]) -> str:
        return await asyncio.to_thread(self._sync_chat, messages)

    async def ping(self) -> dict:
        return {"reachable": True, "note": "not probed (avoids spending tokens)"}
