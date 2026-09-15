"""Centralized application configuration using Pydantic Settings.

All environment variables must be defined here so that changing providers
or configurations requires no modifications to application code.
No other file in the application should call os.environ directly.
"""

from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Database Settings
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "lenny_growth"
    DATABASE_URL: str = "postgresql://postgres:postgres@db:5432/lenny_growth"

    # LLM Provider Configuration (defaults to local Ollama)
    LLM_PROVIDER: str = "ollama"
    OLLAMA_BASE_URL: str = "http://host.docker.internal:11434"
    OLLAMA_MODEL: str = "llama3.1:8b"
    ANTHROPIC_API_KEY: Optional[str] = None

    # API Configuration
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


# Global settings singleton instance
settings = Settings()
