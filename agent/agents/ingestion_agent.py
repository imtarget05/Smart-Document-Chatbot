"""
Ingestion Agent.

Coordinates enterprise data source ingestion into Qdrant so RAG agents can
search uploaded files and connector-backed sources through the same interface.
"""

import logging
from typing import Any, Dict, List, Type

from connectors.gmail import GmailConnector
from connectors.google_drive import GoogleDriveConnector
from connectors.sharepoint import SharePointConnector
from connectors.slack_connector import SlackConnector

logger = logging.getLogger(__name__)


class IngestionAgent:
    _connectors: Dict[str, Type] = {
        "google_drive": GoogleDriveConnector,
        "gmail": GmailConnector,
        "slack": SlackConnector,
        "sharepoint": SharePointConnector,
    }

    async def ingest(
        self, source: str, user_id: str, params: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        connector_cls = self._connectors.get(source)
        if not connector_cls:
            raise ValueError(f"Unknown connector source: {source}")
        connector = connector_cls()
        logger.info("IngestionAgent source=%s user=%s", source, user_id)
        return await connector.ingest(user_id=user_id, params=params or {})

    @classmethod
    def supported_sources(cls) -> List[str]:
        return sorted(cls._connectors.keys())
