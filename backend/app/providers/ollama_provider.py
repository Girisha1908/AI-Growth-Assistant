"""Local inference through Ollama (the mandatory demo path)."""

import asyncio
from typing import Optional

import requests

from app.config import settings
from app.providers.base import LLMProvider


class OllamaProvider(LLMProvider):
    name = "ollama"

    def __init__(self, base_url: Optional[str] = None, model: Optional[str] = None,
                 temperature: float = 0.2, timeout: Optional[int] = None):
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.model = model or settings.OLLAMA_MODEL
        self.temperature = temperature
        self.timeout = timeout or settings.OLLAMA_TIMEOUT_SECONDS

    def _sync_chat(self, messages: list[dict]) -> str:
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": self.temperature, "num_ctx": settings.OLLAMA_NUM_CTX},
        }
        try:
            response = requests.post(url, json=payload, timeout=self.timeout)
            if response.status_code == 404:
                raise RuntimeError(
                    f"Ollama model '{self.model}' not found. Run: ollama pull {self.model}")
            response.raise_for_status()
            answer = response.json().get("message", {}).get("content", "").strip()
            if not answer:
                raise RuntimeError("Empty response received from Ollama model")
            return answer
        except requests.exceptions.ConnectionError as e:
            raise ConnectionError(
                f"Cannot connect to Ollama at {self.base_url}. Is the Ollama app running?") from e
        except requests.exceptions.Timeout as e:
            raise TimeoutError(f"Ollama generation timed out after {self.timeout}s") from e
        except RuntimeError:
            raise
        except Exception as e:  # noqa: BLE001
            raise RuntimeError(f"Ollama generation error: {e}") from e

    async def chat(self, messages: list[dict]) -> str:
        return await asyncio.to_thread(self._sync_chat, messages)

    def _sync_ping(self) -> dict:
        try:
            r = requests.get(f"{self.base_url}/api/tags", timeout=3)
            r.raise_for_status()
            names = [m.get("name", "") for m in r.json().get("models", [])]
            want = self.model if ":" in self.model else self.model + ":latest"
            have = want in names or self.model in names
            return {"reachable": True, "model_installed": have,
                    "embed_model_installed": any(n.startswith(settings.OLLAMA_EMBED_MODEL)
                                                 for n in names)}
        except Exception as e:  # noqa: BLE001
            return {"reachable": False, "error": str(e)[:200]}

    async def ping(self) -> dict:
        return await asyncio.to_thread(self._sync_ping)
