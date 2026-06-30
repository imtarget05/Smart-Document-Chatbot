"""
Agent service settings – loaded from environment variables / .env
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file="../.env", env_file_encoding="utf-8", extra="ignore")

    # Spring Boot internal auth
    internal_service_token: str = "local-development-service-token-change-me"

    # Ollama-compatible LLM Router (local / Claude / GPT-4o)
    llm_base_url: str = "http://llm-router:8000"
    llm_chat_model: str = "llama3.2:3b"
    llm_embedding_model: str = "nomic-embed-text"
    llm_temperature: float = 0.3

    # OpenRouter (Reasoning Tasks)
    openrouter_api_key: str = ""
    reasoning_model: str = "google/gemini-2.0-flash-001"  # Default reasoning model

    # Qdrant
    qdrant_host: str = "qdrant"
    qdrant_port: int = 6333
    qdrant_api_key: str = "qdrant_key_123"

    # PostgreSQL (long-term memory)
    postgres_db: str = "smart_doc_chatbot"
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"
    postgres_host: str = "postgres"
    postgres_port: int = 5432

    # Tavily (web search)
    tavily_api_key: str = ""

    # Phase 3 – Google
    google_credentials_json: str = ""       # path to credentials.json or inline JSON
    google_token_json: str = ""             # path to token.json

    # Phase 3 – Slack
    slack_bot_token: str = ""

    # Connector ingestion
    connector_chunk_size: int = 1200
    connector_chunk_overlap: int = 180

    # Microsoft SharePoint / Graph
    sharepoint_mock_enabled: bool = True
    microsoft_graph_token: str = ""
    sharepoint_site_id: str = ""
    sharepoint_drive_id: str = ""

    # Phase 4 – Email (SMTP)
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""

    # Phase 4 – Webhooks / integrations
    jira_base_url: str = ""
    jira_email: str = ""
    jira_api_token: str = ""
    notion_api_token: str = ""
    teams_webhook_url: str = ""

    # ── Security ────────────────────────────────────────────────────────────
    # Comma-separated list of origins allowed to call this service from a browser.
    # CORS only matters for browser callers; Spring Boot internal calls bypass it.
    # Set AGENT_ALLOWED_ORIGINS in .env for production.
    agent_allowed_origins: str = "http://localhost:3000,http://localhost:8080,http://127.0.0.1:3000"

    # Maximum body size (bytes) accepted by agent endpoints.
    # Prevents prompt-injection via oversized payloads (default 512 KB).
    agent_max_request_bytes: int = 524_288  # 512 KB

    # Rate limiting per authenticated user-id (requests per minute).
    # LLM calls are expensive; keep this conservative.
    agent_rate_limit_rpm: int = 20

    # ── Redis (rate limiting + short-term memory) ────────────────────────────
    # Optional. When set, the rate limiter uses Redis sorted-sets for accurate
    # per-IP counting across multiple replicas. Falls back to in-memory if blank.
    # Example: redis://redis:6379/0
    redis_url: str = ""


settings = Settings()
