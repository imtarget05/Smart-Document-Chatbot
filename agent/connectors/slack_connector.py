"""
Slack Connector – Phase 3.
Pulls messages from specified Slack channels and makes them available
for ingestion into the RAG pipeline.

Required env vars:
  SLACK_BOT_TOKEN – Bot token with channels:history scope
"""

import logging
from typing import Any, Dict, List

from settings import settings

logger = logging.getLogger(__name__)


class SlackConnector:
    async def ingest(self, user_id: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        params:
          channel_id  – Slack channel ID (e.g. "C1234567890")
          oldest      – oldest message timestamp (Unix ts string)
          limit       – max messages per channel (default 100)
        """
        if not settings.slack_bot_token:
            logger.warning("Slack not configured (SLACK_BOT_TOKEN missing) – skipping")
            return []

        import asyncio
        from slack_sdk.web.async_client import AsyncWebClient

        client     = AsyncWebClient(token=settings.slack_bot_token)
        channel_id = params.get("channel_id", "")
        limit      = int(params.get("limit", 100))
        oldest     = params.get("oldest", "0")

        if not channel_id:
            logger.warning("Slack ingest: no channel_id provided")
            return []

        try:
            response = await client.conversations_history(
                channel=channel_id,
                oldest=oldest,
                limit=limit,
            )
        except Exception as exc:
            logger.error("Slack history fetch failed: %s", exc)
            return []

        messages = response.get("messages", [])
        ingested = []
        for msg in messages:
            text = msg.get("text", "").strip()
            if text:
                ingested.append({
                    "ts":          msg.get("ts"),
                    "user":        msg.get("user", "unknown"),
                    "text":        text,
                    "text_length": len(text),
                })

        logger.info("Slack: pulled %d messages from channel %s for user %s",
                    len(ingested), channel_id, user_id)
        return ingested
