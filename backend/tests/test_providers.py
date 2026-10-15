import asyncio

import pytest

from app.config import get_llm_provider
from app.errors import provider_error_from
from app.providers.claude_agent_provider import ClaudeAgentProvider
from app.providers.claude_provider import ClaudeProvider
from app.providers.ollama_provider import OllamaProvider


def test_factory_selects_by_name_only():
    assert isinstance(get_llm_provider("ollama"), OllamaProvider)
    with pytest.raises(ValueError, match="Unsupported"):
        get_llm_provider("gpt-nine")


def test_cloud_providers_need_a_key_but_import_fine():
    with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
        ClaudeProvider()
    with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
        ClaudeAgentProvider()
    assert ClaudeProvider(api_key="sk-test").model
    assert ClaudeAgentProvider(api_key="sk-test").name == "claude-agent"


def test_ollama_unreachable_maps_to_connection_error():
    p = OllamaProvider(base_url="http://127.0.0.1:9", timeout=2)
    with pytest.raises(ConnectionError, match="Ollama"):
        asyncio.run(p.chat([{"role": "user", "content": "hi"}]))
    assert asyncio.run(p.ping())["reachable"] is False


def test_error_mapping():
    assert provider_error_from(ValueError("no key")).status == 400
    assert provider_error_from(ConnectionError("x")).code == "provider_unavailable"
    assert provider_error_from(TimeoutError("x")).status == 504
