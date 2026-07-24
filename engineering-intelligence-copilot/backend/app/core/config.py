from functools import lru_cache
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Engineering Intelligence Copilot API"
    environment: str = "development"
    debug: bool = True
    api_v1_prefix: str = "/api/v1"

    cors_origins: List[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://localhost:5173",
        ]
    )

    database_url: str = "sqlite:///./engineering_copilot.db"
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "engineering_knowledge"

    # LLM provider: "ollama" (default for local), "openai", "anthropic", or "mock" (dev only).
    # Issue #36: Changed default from "mock" to "ollama" so real LLM calls are made.
    llm_provider: str = "ollama"
    llm_model: str = "llama3.1:8b"
    llm_base_url: str = "http://localhost:11434"
    embedding_provider: str = "ollama"
    embedding_model: str = "nomic-embed-text"

    # JWT secret - NO insecure default. Must be set via env var in production.
    jwt_secret_key: str = ""
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    upload_dir: str = "./uploads"
    max_upload_size_mb: int = 25
    allowed_extensions: List[str] = Field(
        default_factory=lambda: ["pdf", "docx", "txt", "md", "csv", "json"]
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="EIC_",
        extra="ignore",
    )

    @field_validator("jwt_secret_key")
    @classmethod
    def _validate_jwt_secret(cls, v: str) -> str:
        import os

        env = os.getenv("EIC_ENVIRONMENT", "development").strip().lower()
        if env not in ("development", "dev", "test", "local"):
            if not v or v.lower() in ("change-me", "changeme", "secret", "password"):
                raise ValueError(
                    "EIC_JWT_SECRET_KEY must be set to a strong value in non-development environments."
                )
            if len(v) < 32:
                raise ValueError(
                    "EIC_JWT_SECRET_KEY must be at least 32 characters in non-development environments."
                )
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
