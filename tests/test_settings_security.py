"""
Tests for the security settings validation (issue #1-4, #49).

These tests verify that the Settings class correctly rejects insecure default
secrets in production mode and allows them in local/dev mode.
"""

import sys
from pathlib import Path

import pytest

# Add agent dir to path
_AGENT_DIR = Path(__file__).resolve().parent.parent / "agent"
sys.path.insert(0, str(_AGENT_DIR))


def _reload_settings():
    """Reload the settings module and return it. The module-level
    `settings = Settings()` will raise if validators fail."""
    import importlib
    import settings as settings_mod

    importlib.reload(settings_mod)
    return settings_mod


class TestSettingsSecurity:
    """Test that Settings validators reject insecure secrets in production."""

    def test_production_rejects_empty_internal_token(self, monkeypatch):
        """In production, an empty INTERNAL_SERVICE_TOKEN should be rejected."""
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setenv("INTERNAL_SERVICE_TOKEN", "")
        monkeypatch.setenv("POSTGRES_PASSWORD", "a-valid-strong-password")
        with pytest.raises(Exception):
            _reload_settings()

    def test_production_rejects_short_internal_token(self, monkeypatch):
        """In production, a short INTERNAL_SERVICE_TOKEN should be rejected."""
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setenv("INTERNAL_SERVICE_TOKEN", "short")
        monkeypatch.setenv("POSTGRES_PASSWORD", "a-valid-strong-password")
        with pytest.raises(Exception):
            _reload_settings()

    def test_production_rejects_placeholder_internal_token(self, monkeypatch):
        """In production, a known placeholder token should be rejected."""
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setenv(
            "INTERNAL_SERVICE_TOKEN", "local-development-service-token-change-me"
        )
        monkeypatch.setenv("POSTGRES_PASSWORD", "a-valid-strong-password")
        with pytest.raises(Exception):
            _reload_settings()

    def test_production_rejects_empty_postgres_password(self, monkeypatch):
        """In production, an empty POSTGRES_PASSWORD should be rejected."""
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setenv(
            "INTERNAL_SERVICE_TOKEN", "a-valid-strong-token-32-chars-long!!"
        )
        monkeypatch.setenv("POSTGRES_PASSWORD", "")
        with pytest.raises(Exception):
            _reload_settings()

    def test_production_rejects_postgres_default_password(self, monkeypatch):
        """In production, 'postgres' as password should be rejected."""
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setenv(
            "INTERNAL_SERVICE_TOKEN", "a-valid-strong-token-32-chars-long!!"
        )
        monkeypatch.setenv("POSTGRES_PASSWORD", "postgres")
        with pytest.raises(Exception):
            _reload_settings()

    def test_production_rejects_short_postgres_password(self, monkeypatch):
        """In production, a short POSTGRES_PASSWORD should be rejected."""
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setenv(
            "INTERNAL_SERVICE_TOKEN", "a-valid-strong-token-32-chars-long!!"
        )
        monkeypatch.setenv("POSTGRES_PASSWORD", "short")
        with pytest.raises(Exception):
            _reload_settings()

    def test_production_rejects_localhost_cors(self, monkeypatch):
        """In production, localhost CORS origins should be rejected."""
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setenv(
            "INTERNAL_SERVICE_TOKEN", "a-valid-strong-token-32-chars-long!!"
        )
        monkeypatch.setenv("POSTGRES_PASSWORD", "a-valid-strong-password")
        monkeypatch.setenv("AGENT_ALLOWED_ORIGINS", "http://localhost:3000")
        with pytest.raises(Exception):
            _reload_settings()

    def test_local_allows_empty_secrets(self, monkeypatch):
        """In local mode, empty secrets should be allowed (with warning)."""
        monkeypatch.setenv("APP_ENV", "local")
        monkeypatch.setenv("INTERNAL_SERVICE_TOKEN", "")
        monkeypatch.setenv("POSTGRES_PASSWORD", "")
        monkeypatch.setenv("AGENT_ALLOWED_ORIGINS", "http://localhost:3000")
        settings_mod = _reload_settings()
        s = settings_mod.Settings()
        assert s.internal_service_token == ""
        assert s.postgres_password == ""

    def test_production_accepts_strong_secrets(self, monkeypatch):
        """In production, strong secrets should be accepted."""
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setenv(
            "INTERNAL_SERVICE_TOKEN", "a-very-strong-and-unique-token-32+chars!"
        )
        monkeypatch.setenv("POSTGRES_PASSWORD", "a-very-strong-password-12+chars!")
        monkeypatch.setenv(
            "AGENT_ALLOWED_ORIGINS", "https://app.example.com,https://admin.example.com"
        )
        settings_mod = _reload_settings()
        s = settings_mod.Settings()
        assert len(s.internal_service_token) >= 32
        assert len(s.postgres_password) >= 12
        assert "localhost" not in s.agent_allowed_origins

    def test_qdrant_key_placeholder_rejected(self, monkeypatch):
        """A known placeholder QDRANT_API_KEY should be rejected."""
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setenv(
            "INTERNAL_SERVICE_TOKEN", "a-valid-strong-token-32-chars-long!!"
        )
        monkeypatch.setenv("POSTGRES_PASSWORD", "a-valid-strong-password")
        monkeypatch.setenv("QDRANT_API_KEY", "qdrant_key_123")
        with pytest.raises(Exception):
            _reload_settings()

    def test_qdrant_key_empty_allowed(self, monkeypatch):
        """An empty QDRANT_API_KEY should be allowed (local unauthenticated Qdrant)."""
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setenv(
            "INTERNAL_SERVICE_TOKEN", "a-valid-strong-token-32-chars-long!!"
        )
        monkeypatch.setenv("POSTGRES_PASSWORD", "a-valid-strong-password")
        monkeypatch.setenv("QDRANT_API_KEY", "")
        monkeypatch.setenv("AGENT_ALLOWED_ORIGINS", "https://app.example.com")
        settings_mod = _reload_settings()
        s = settings_mod.Settings()
        assert s.qdrant_api_key == ""
