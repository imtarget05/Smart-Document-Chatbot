"""
Gmail Connector – Phase 3.
Pulls recent emails matching a query, extracts plain-text content,
and makes them available for ingestion into the RAG pipeline.

Required env vars:
  GOOGLE_CREDENTIALS_JSON
  GOOGLE_TOKEN_JSON
"""

import logging
import base64
from typing import Any, Dict, List

from ingestion.pipeline import ConnectorIngestionPipeline
from settings import settings

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/drive.readonly",  # shared auth
]


class GmailConnector:
    async def ingest(
        self, user_id: str, params: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        documents = await self.fetch_documents(user_id=user_id, params=params)
        return await ConnectorIngestionPipeline().ingest_documents(user_id, documents)

    async def fetch_documents(
        self, user_id: str, params: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        params:
          gmail_query   – Gmail search query (e.g. "from:boss@co.com subject:report")
          max_emails    – max emails to fetch (default 20)
        """
        if not settings.google_credentials_json:
            logger.warning("Gmail not configured – skipping")
            return []

        import asyncio

        loop = asyncio.get_event_loop()

        try:
            service = await loop.run_in_executor(None, self._build_service)
        except Exception as exc:
            logger.error("Gmail auth failed: %s", exc)
            return []

        gmail_query = params.get("gmail_query", "")
        max_emails = int(params.get("max_emails", 20))

        def _list_messages():
            return (
                service.users()
                .messages()
                .list(userId="me", q=gmail_query, maxResults=max_emails)
                .execute()
                .get("messages", [])
            )

        messages = await loop.run_in_executor(None, _list_messages)
        documents = []

        for msg_ref in messages[:max_emails]:
            text, subject = await self._get_email_text(service, msg_ref["id"], loop)
            if text:
                documents.append(
                    {
                        "source": "gmail",
                        "external_id": msg_ref["id"],
                        "title": subject or f"Gmail message {msg_ref['id']}",
                        "text": text,
                        "metadata": {
                            "subject": subject,
                            "gmail_query": gmail_query,
                        },
                    }
                )

        logger.info("Gmail: pulled %d emails for user %s", len(documents), user_id)
        return documents

    def _build_service(self):
        import os
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build

        creds = None
        token_path = settings.google_token_json or "token.json"
        creds_path = settings.google_credentials_json

        if os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
                creds = flow.run_local_server(port=0)
            with open(token_path, "w") as token:
                token.write(creds.to_json())
        return build("gmail", "v1", credentials=creds)

    async def _get_email_text(self, service, msg_id: str, loop) -> tuple:
        def _fetch():
            return (
                service.users()
                .messages()
                .get(userId="me", id=msg_id, format="full")
                .execute()
            )

        try:
            msg = await loop.run_in_executor(None, _fetch)
            headers = {h["name"]: h["value"] for h in msg["payload"].get("headers", [])}
            subject = headers.get("Subject", "")
            body = self._extract_body(msg["payload"])
            return body, subject
        except Exception as exc:
            logger.warning("Failed to fetch email %s: %s", msg_id, exc)
            return "", ""

    def _extract_body(self, payload: Dict) -> str:
        if "parts" in payload:
            for part in payload["parts"]:
                if part.get("mimeType") == "text/plain":
                    data = part.get("body", {}).get("data", "")
                    if data:
                        return base64.urlsafe_b64decode(data).decode(
                            "utf-8", errors="ignore"
                        )
        body_data = payload.get("body", {}).get("data", "")
        if body_data:
            return base64.urlsafe_b64decode(body_data).decode("utf-8", errors="ignore")
        return ""
