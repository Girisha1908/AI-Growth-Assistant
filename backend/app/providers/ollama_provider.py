"""Ollama provider implementation for local LLM inference."""

import asyncio
from typing import Optional
import requests

from app.config import settings
from app.providers.base import LLMProvider


class OllamaProvider(LLMProvider):
    """LLM provider implementation for local Ollama instances."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.2,
        timeout: int = 300,
    ):
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.model = model or settings.OLLAMA_MODEL
        self.temperature = temperature
        self.timeout = timeout

    def _sync_chat(self, messages: list[dict]) -> str:
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": self.temperature,
            },
        }

        try:
            response = requests.post(url, json=payload, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            answer = data.get("message", {}).get("content", "").strip()
            if not answer:
                raise RuntimeError("Empty response received from Ollama model")
            return answer
        except requests.exceptions.ConnectionError as e:
            raise ConnectionError(
                f"Cannot connect to Ollama at {url} — is the model server running?"
            ) from e
        except requests.exceptions.Timeout as e:
            raise TimeoutError("Ollama generation timed out") from e
        except requests.exceptions.HTTPError as e:
            raise RuntimeError(f"Ollama HTTP error {response.status_code}: {response.text}") from e
        except Exception as e:
            raise RuntimeError(f"Ollama generation error: {e}") from e

    async def chat(self, messages: list[dict]) -> str:
        """Asynchronously invoke Ollama's chat API in a worker thread."""
        return await asyncio.to_thread(self._sync_chat, messages)
