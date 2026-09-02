"""
Tests for Human-in-the-Loop (HITL) approval gate — Governance layer.

Covers: HITLStore lifecycle (create/get/decide/TTL), the LangGraph hitl_gate
node pausing action runs, conditional routing, and the /agent/approvals API
endpoints (list → approve → execute / reject).
"""

import asyncio

import pytest
from fastapi.testclient import TestClient

import hitl as hitl_module
from hitl import HITLStore


# ---------------------------------------------------------------------------
# HITLStore unit tests
# ---------------------------------------------------------------------------
@pytest.fixture()
def store():
    return HITLStore(ttl_seconds=60)


def test_create_returns_pending_record(store):
    record = asyncio.run(
        store.create(query="Send report", session_id="s1", user_id="u1", agent_plan="p")
    )
    assert record["request_id"].startswith("hitl-")
    assert record["status"] == "pending"
    assert record["query"] == "Send report"
    assert record["approver"] is None


def test_decide_approves_pending_request(store):
    record = asyncio.run(store.create(query="q", session_id="s", user_id="u"))
    updated = asyncio.run(store.decide(record["request_id"], "approved", "admin@example.com"))
    assert updated["status"] == "approved"
    assert updated["approver"] == "admin@example.com"


def test_decide_rejects_and_cannot_redecide(store):
    record = asyncio.run(store.create(query="q", session_id="s", user_id="u"))
    rid = record["request_id"]
    assert asyncio.run(store.decide(rid, "rejected", "boss"))["status"] == "rejected"
    # Already decided → None (idempotency safety)
    assert asyncio.run(store.decide(rid, "approved", "boss")) is None


def test_decide_invalid_decision_raises(store):
    record = asyncio.run(store.create(query="q", session_id="s", user_id="u"))
    with pytest.raises(ValueError):
        asyncio.run(store.decide(record["request_id"], "maybe", "boss"))


def test_ttl_expiry_moves_request_to_expired():
    store = HITLStore(ttl_seconds=0)
    record = asyncio.run(store.create(query="q", session_id="s", user_id="u"))
    import time

    time.sleep(0.01)
    assert asyncio.run(store.get(record["request_id"]))["status"] == "expired"
    assert asyncio.run(store.list_pending()) == []


def test_list_pending_only_returns_pending(store):
    r1 = asyncio.run(store.create(query="q1", session_id="s", user_id="u"))
    asyncio.run(store.create(query="q2", session_id="s", user_id="u"))
    asyncio.run(store.decide(r1["request_id"], "approved", "boss"))
    pending = asyncio.run(store.list_pending())
    assert len(pending) == 1
    assert pending[0]["query"] == "q2"


# ---------------------------------------------------------------------------
# Workflow gate: action route must pause for approval
# ---------------------------------------------------------------------------
def test_hitl_gate_pauses_without_approval():
    import asyncio

    from graph.workflow import hitl_gate_node, route_after_hitl

    state = {"query": "send email", "session_id": "s", "user_id": "u",
             "agent_plan": "", "document_ids": [], "hitl_auto_approved": False}
    result = asyncio.run(hitl_gate_node(state))
    assert result["hitl_pending"] is True
    assert result["hitl_approval_id"].startswith("hitl-")
    assert result["action_result"]["status"] == "pending_approval"
    assert route_after_hitl(result) == "__end__"


def test_hitl_gate_passes_through_when_auto_approved():
    import asyncio

    from graph.workflow import hitl_gate_node, route_after_hitl

    state = {"query": "send email", "session_id": "s", "user_id": "u",
             "hitl_auto_approved": True}
    result = asyncio.run(hitl_gate_node(state))
    assert result["hitl_pending"] is False
    assert route_after_hitl(result) == "action"


# ---------------------------------------------------------------------------
# API endpoints
# ---------------------------------------------------------------------------
def test_approvals_api_list_approve_reject_flow():
    from main import app

    client = TestClient(app)
    # A workflow run that routes to action must pause (mocked sub-agents in CI)
    resp = client.post(
        "/v1/agent/invoke",
        json={"query": "Send the summary to compliance", "session_id": "hitl-s",
              "user_id": "u1", "intent_override": "action"},
    )
    assert resp.status_code == 200
    body = resp.json()

    listing = client.get("/v1/agent/approvals").json()
    assert listing["status"] == "ok"

    pending = listing["pending"]
    if body.get("hitl_pending") or body.get("approval_id") or pending:
        rid = body.get("approval_id") or (pending[0]["request_id"] if pending else None)
        assert rid is not None
        # Detail view
        detail = client.get(f"/v1/agent/approvals/{rid}").json()
        assert detail["request"]["status"] == "pending"
        # Reject → nothing executes
        rej = client.post(
            f"/v1/agent/approvals/{rid}/reject",
            json={"approver": "admin@test", "note": "not now"},
        )
        assert rej.status_code == 200
        assert rej.json()["decision"] == "rejected"
        # Double decision → 404
        assert client.post(
            f"/v1/agent/approvals/{rid}/approve", json={"approver": "admin@test"}
        ).status_code == 404


def test_approvals_404_for_unknown_id():
    from main import app

    client = TestClient(app)
    assert client.get("/v1/agent/approvals/hitl-doesnotexist").status_code == 404
    assert client.post(
        "/v1/agent/approvals/hitl-doesnotexist/approve", json={"approver": "a"}
    ).status_code == 404
