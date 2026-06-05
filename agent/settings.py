"""
Agent service settings – loaded from environment variables / .env
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file="../.env", env_file_encoding="utf-8", extra="ignore")

    # Spring Boot internal auth
    internal_service_token: str = "local-development-service-token-change-me"

    # Ollama (Local Tasks)
    llm_base_url: str = "http://llm:11434"
    llm_chat_model: str = "deepseek-r1:1.5b"
    llm_embedding_model: str = "nomic-embed-text"
    llm_temperature: float = 0.3

    # OpenRouter (Reasoning Tasks)
    openrouter_api_key: str = ""
    reasoning_model: str = "google/gemini-2.0-flash-001" # Default reasoning model

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


settings = Settings()
