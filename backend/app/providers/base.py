"""The one interface every model backend must satisfy.

Application code (agent, skills, routers) imports ONLY this. Which concrete
class sits behind it is decided by config -- that is what makes the model
toggle real rather than cosmetic.
"""

from abc import ABC, abstractmethod


class LLMProvider(ABC):
    name: str = "base"
    model: str = ""

    @abstractmethod
    async def chat(self, messages: list[dict]) -> str:
        """messages: [{'role': 'system'|'user'|'assistant', 'content': str}, ...]

        Returns the assistant text. Raises:
          ValueError       provider misconfigured (e.g. missing API key)
          ConnectionError  provider unreachable
          TimeoutError     provider too slow
          RuntimeError     anything else
        """

    async def ping(self) -> dict:
        """Cheap reachability check for /health. Never raises."""
        return {"reachable": True}
