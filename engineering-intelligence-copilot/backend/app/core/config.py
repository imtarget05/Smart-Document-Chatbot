from functools import lru_cache
from typing import List

from pydantic import Field
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

    llm_provider: str = "mock"
    llm_model: str = "llama3.1:8b"
    embedding_provider: str = "mock"
    embedding_model: str = "nomic-embed-text"

    jwt_secret_key: str = "change-me"
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


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()