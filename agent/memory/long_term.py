"""
Long-term memory – stores user preferences and history in PostgreSQL.
Uses asyncpg for non-blocking DB access.
"""

import json
import logging
from typing import Any, Dict, List, Optional

from settings import settings

logger = logging.getLogger(__name__)


class LongTermMemory:
    def __init__(self):
        self._pool = None

    async def init(self) -> None:
        try:
            import asyncpg
            dsn = (
                f"postgresql://{settings.postgres_user}:{settings.postgres_password}"
                f"@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
            )
            self._pool = await asyncpg.create_pool(dsn, min_size=1, max_size=5)
            await self._create_tables()
            logger.info("Long-term memory connected to PostgreSQL")
        except Exception as exc:
            logger.warning("Long-term memory DB init failed: %s – operating without persistence", exc)

    async def _create_tables(self) -> None:
        if not self._pool:
            return
        async with self._pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS agent_user_prefs (
                    user_id  TEXT PRIMARY KEY,
                    prefs    JSONB NOT NULL DEFAULT '{}'
                )
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS agent_session_history (
                    id         BIGSERIAL PRIMARY KEY,
                    user_id    TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    role       TEXT NOT NULL,
                    content    TEXT NOT NULL,
                    agent_type TEXT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_agent_session_history_session
                ON agent_session_history (session_id, created_at DESC)
            """)

    async def save_turn(self, user_id: str, session_id: str, role: str,
                        content: str, agent_type: str = "") -> None:
        if not self._pool:
            return
        try:
            async with self._pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO agent_session_history (user_id, session_id, role, content, agent_type)
                    VALUES ($1, $2, $3, $4, $5)
                    """,
                    user_id, session_id, role, content, agent_type,
                )
        except Exception as exc:
            logger.warning("Failed to save turn: %s", exc)

    async def get_history(self, session_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        if not self._pool:
            return []
        try:
            async with self._pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT role, content, agent_type, created_at
                    FROM agent_session_history
                    WHERE session_id = $1
                    ORDER BY created_at DESC
                    LIMIT $2
                    """,
                    session_id, limit,
                )
            return [dict(r) for r in reversed(rows)]
        except Exception as exc:
            logger.warning("Failed to fetch history: %s", exc)
            return []

    async def get_user_prefs(self, user_id: str) -> Dict[str, Any]:
        if not self._pool:
            return {}
        try:
            async with self._pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT prefs FROM agent_user_prefs WHERE user_id = $1", user_id
                )
            return json.loads(row["prefs"]) if row else {}
        except Exception as exc:
            logger.warning("Failed to fetch user prefs: %s", exc)
            return {}

    async def set_user_prefs(self, user_id: str, prefs: Dict[str, Any]) -> None:
        if not self._pool:
            return
        try:
            async with self._pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO agent_user_prefs (user_id, prefs) VALUES ($1, $2::jsonb)
                    ON CONFLICT (user_id) DO UPDATE SET prefs = EXCLUDED.prefs
                    """,
                    user_id, json.dumps(prefs),
                )
        except Exception as exc:
            logger.warning("Failed to save user prefs: %s", exc)
