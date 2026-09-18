"""Health contract for the LLM router: /health/live is dependency-free,
/health/ready reports local/cloudflare serving-path checks."""
from fastapi.testclient import TestClient

from app.main import create_app

client = TestClient(create_app())


def test_live_ok_without_dependencies():
    r = client.get("/health/live")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_ready_reports_checks():
    r = client.get("/health/ready")
    assert r.status_code in (200, 503)
    body = r.json()
    assert body["status"] in ("ready", "not-ready")
    assert "checks" in body
    assert "local" in body["checks"]
    assert "cloudflare" in body["checks"]


def test_legacy_health_still_served():
    assert client.get("/health").status_code == 200
