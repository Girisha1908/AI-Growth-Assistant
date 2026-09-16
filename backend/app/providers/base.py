"""Base interface for swappable LLM providers.

Defines the contract that all LLM implementations (Ollama, Claude, etc.)
must satisfy to be used interchangeably by the /chat endpoint.
"""

from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """Abstract interface that all LLM providers must implement.

    Any provider (Ollama, Claude, etc.) must expose an asynchronous chat
    method accepting standard role/content messages and returning the
    assistant's synthesized text response.
    """

    @abstractmethod
    async def chat(self, messages: list[dict]) -> str:
        """Send chat messages to the model provider and return the response text.

        Args:
            messages: List of message dictionaries with 'role' and 'content' keys.
                      E.g., [{'role': 'system', 'content': ...}, {'role': 'user', 'content': ...}]

        Returns:
            The generated response string.

        Raises:
            Exception: If provider communication fails or returns an unrecoverable error.
        """
        pass
