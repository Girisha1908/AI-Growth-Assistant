"""Centralized application configuration (Pydantic Settings).

Rule: every environment variable is declared here and nowhere else. Changing
the model, the provider or any retrieval knob therefore never needs a code
change -- only `.env`.
"""

from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ── Database ────────────────────────────────────────────────────
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "lenny_growth"
    DATABASE_URL: str = "postgresql://postgres:postgres@db:5432/lenny_growth"

    # ── LLM provider: "ollama" | "claude" | "claude-agent" ─────────
    LLM_PROVIDER: str = "ollama"
    OLLAMA_BASE_URL: str = "http://host.docker.internal:11434"
    OLLAMA_MODEL: str = "llama3.2:3b"
    OLLAMA_TIMEOUT_SECONDS: int = 600
    # Ollama silently truncates prompts longer than num_ctx. 4 chunks of ~500
    # words need ~3-4k tokens, so we ask for a bigger window explicitly.
    OLLAMA_NUM_CTX: int = 8192
    ANTHROPIC_API_KEY: Optional[str] = None
    CLAUDE_MODEL: str = "claude-sonnet-5-5"

    # ── Embeddings / retrieval ──────────────────────────────────────
    OLLAMA_EMBED_MODEL: str = "nomic-embed-text"
    EMBED_BATCH_SIZE: int = 16
    # nomic-embed-text recommends "search_document:" / "search_query:" prefixes.
    # OFF by default because the relevance threshold below was calibrated
    # without them. If you turn this on, re-ingest AND re-run `eval/run_eval.py`.
    EMBED_USE_PREFIXES: bool = False
    RETRIEVAL_TOP_K: int = 4
    RETRIEVAL_CANDIDATES: int = 20
    # Cosine distance (0 = identical). Best vector hit farther than this => refuse.
    RELEVANCE_MAX_DISTANCE: float = 0.45
    # Keyword-only hits may be slightly less similar than pure vector hits.
    KEYWORD_DISTANCE_MARGIN: float = 0.10
    MAX_CHUNKS_PER_EPISODE: int = 2
    HISTORY_MESSAGES: int = 6

    # ── Skills ──────────────────────────────────────────────────────
    SHIP30_TARGET_WORDS: int = 1250
    # "sectioned" = outline + one call per section (reaches length on small
    # models). "single" = one long generation.
    SHIP30_STRATEGY: str = "sectioned"
    ARTIFACT_MAX_BYTES: int = 200_000

    # ── Ingestion ───────────────────────────────────────────────────
    TRANSCRIPTS_DIR: str = "/app/transcripts/source"
    CHUNK_WORDS: int = 500
    CHUNK_OVERLAP_WORDS: int = 50

    # ── API ─────────────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ]
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def embed_tag(self) -> str:
        """Identifies HOW chunks were embedded. Vectors from different tags must
        never be compared, so we store this on every chunk."""
        return self.OLLAMA_EMBED_MODEL + ("+prefix" if self.EMBED_USE_PREFIXES else "")


settings = Settings()


def get_llm_provider(provider_name: Optional[str] = None):
    """Factory: returns the configured LLMProvider. Application code only ever
    sees the LLMProvider interface, never a concrete class."""
    selected = (provider_name or settings.LLM_PROVIDER).lower().strip()
    if selected == "ollama":
        from app.providers.ollama_provider import OllamaProvider

        return OllamaProvider()
    if selected == "claude":
        from app.providers.claude_provider import ClaudeProvider

        return ClaudeProvider()
    if selected in ("claude-agent", "claude_agent"):
        from app.providers.claude_agent_provider import ClaudeAgentProvider

        return ClaudeAgentProvider()
    raise ValueError(
        f"Unsupported LLM provider '{selected}'. Supported: 'ollama', 'claude', 'claude-agent'."
    )


def available_providers() -> list[dict]:
    """What the UI may offer. 'configured' means usable without extra setup."""
    key_ok = bool(settings.ANTHROPIC_API_KEY and settings.ANTHROPIC_API_KEY.strip())
    return [
        {"name": "ollama", "label": f"Ollama ({settings.OLLAMA_MODEL})", "configured": True},
        {"name": "claude", "label": f"Claude ({settings.CLAUDE_MODEL})", "configured": key_ok},
        {"name": "claude-agent", "label": "Claude Agent SDK", "configured": key_ok},
    ]
