"""
Human-in-the-Loop (HITL) approval store — Governance gate for agentic actions.

Any orchestrator-routed action (send_email, create_jira, create_notion,
webhook...) must be approved by a human before it executes. This module holds
pending approval requests in-memory with a TTL; the LangGraph `hitl_gate` node
creates requests and the /agent/approvals endpoints decide them.

Note: the store is per-process (single agent-service replica). For multi-replica
deployments back this with Redis — same contract as jobs.py.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import Any, Dict, List, Optional

from settings import settings

logger = logging.getLogger(__name__)


class HITLStore:
    """In-memory store of pending human-approval requests with TTL expiry."""

    def __init__(self, ttl_seconds: Optional[int] = None):
        self._ttl = ttl_seconds if ttl_seconds is not None else settings.hitl_approval_ttl_seconds
        self._lock = asyncio.Lock()
        self._requests: Dict[str, Dict[str, Any]] = {}

    # ------------------------------------------------------------------
    def _evict_expired(self) -> None:
        now = time.monotonic()
        expired = [
            rid
            for rid, r in self._requests.items()
            if r["status"] == "pending" and now - r["created_at"] > self._ttl
        ]
        for rid in expired:
            self._requests[rid]["status"] = "expired"
            logger.info("HITL request %s expired after %ss", rid, self._ttl)

    # ------------------------------------------------------------------
    async def create(
        self,
        query: str,
        session_id: str,
        user_id: str,
        agent_plan: str = "",
        document_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        async with self._lock:
            self._evict_expired()
            request_id = f"hitl-{uuid.uuid4().hex[:12]}"
            record = {
                "request_id": request_id,
                "query": query,
                "session_id": session_id,
                "user_id": user_id,
                "agent_plan": agent_plan,
                "document_ids": document_ids or [],
                "status": "pending",  # pending | approved | rejected | expired
                "approver": None,
                "note": None,
                "created_at": time.monotonic(),
            }
            self._requests[request_id] = record
            logger.info("HITL request created: %s (query=%s)", request_id, query[:80])
            return dict(record)

    # ------------------------------------------------------------------
    async def get(self, request_id: str) -> Optional[Dict[str, Any]]:
        async with self._lock:
            self._evict_expired()
            record = self._requests.get(request_id)
            return dict(record) if record else None

    # ------------------------------------------------------------------
    async def decide(
        self, request_id: str, decision: str, approver: str, note: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Mark a pending request approved/rejected. Returns updated record."""
        if decision not in {"approved", "rejected"}:
            raise ValueError(f"Invalid decision: {decision}")
        async with self._lock:
            self._evict_expired()
            record = self._requests.get(request_id)
            if record is None or record["status"] != "pending":
                return None
            record["status"] = decision
            record["approver"] = approver
            record["note"] = note
            logger.info(
                "HITL request %s %s by %s", request_id, decision, approver
            )
            return dict(record)

    # ------------------------------------------------------------------
    async def list_pending(self) -> List[Dict[str, Any]]:
        async with self._lock:
            self._evict_expired()
            return [
                dict(r)
                for r in self._requests.values()
                if r["status"] == "pending"
            ]


# Module-level singleton used by the workflow gate and the API endpoints.
hitl_store = HITLStore()
