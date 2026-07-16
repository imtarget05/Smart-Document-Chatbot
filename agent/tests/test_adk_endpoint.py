from fastapi.testclient import TestClient

from main import app


def test_adk_demo_endpoint_returns_workflow_result():
    client = TestClient(app)
    response = client.post(
        "/agent/adk/demo",
        json={"user_request": "Summarize the report", "document_name": "demo.pdf"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["document_name"] == "demo.pdf"
    assert len(body["steps"]) == 5
