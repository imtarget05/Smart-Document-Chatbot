"""
Google Drive Connector – Phase 3.
Pulls files from the user's Google Drive, downloads text content,
and ingests into Qdrant via the embedding pipeline.

Required env vars:
  GOOGLE_CREDENTIALS_JSON – path to OAuth2 credentials.json
  GOOGLE_TOKEN_JSON        – path to token.json (auto-created on first auth)
"""

import logging
import os
from typing import Any, Dict, List

from ingestion.pipeline import ConnectorIngestionPipeline
from settings import settings

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


class GoogleDriveConnector:
    async def ingest(self, user_id: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        documents = await self.fetch_documents(user_id=user_id, params=params)
        return await ConnectorIngestionPipeline().ingest_documents(user_id, documents)

    async def fetch_documents(self, user_id: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        params:
          folder_id (optional) – Drive folder ID to pull from
          max_files (optional) – max number of files to ingest (default 10)
          mime_types (optional) – list of MIME types to filter
        """
        if not settings.google_credentials_json:
            logger.warning("Google Drive not configured – skipping")
            return []

        try:
            service = self._build_service()
        except Exception as exc:
            logger.error("Google Drive auth failed: %s", exc)
            return []

        folder_id  = params.get("folder_id")
        max_files  = int(params.get("max_files", 10))
        mime_types = params.get("mime_types", [
            "text/plain",
            "application/pdf",
            "application/vnd.google-apps.document",
        ])

        # Build query
        q_parts = ["trashed = false"]
        if folder_id:
            q_parts.append(f"'{folder_id}' in parents")
        if mime_types:
            mt_query = " or ".join(f"mimeType='{m}'" for m in mime_types)
            q_parts.append(f"({mt_query})")
        query = " and ".join(q_parts)

        import asyncio
        loop = asyncio.get_event_loop()

        def _list_files():
            return (
                service.files()
                .list(q=query, pageSize=max_files, fields="files(id,name,mimeType)")
                .execute()
                .get("files", [])
            )

        files = await loop.run_in_executor(None, _list_files)
        documents = []
        for f in files[:max_files]:
            text = await self._download_text(service, f)
            if text:
                documents.append({
                    "source": "google_drive",
                    "external_id": f["id"],
                    "title": f["name"],
                    "text": text,
                    "metadata": {
                        "mime_type": f.get("mimeType", ""),
                    },
                })

        logger.info("Google Drive: pulled %d files for user %s", len(documents), user_id)
        return documents

    def _build_service(self):
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

        return build("drive", "v3", credentials=creds)

    async def _download_text(self, service, file_info: Dict) -> str:
        import asyncio
        loop = asyncio.get_event_loop()
        fid  = file_info["id"]
        mime = file_info.get("mimeType", "")

        def _export():
            if mime == "application/vnd.google-apps.document":
                return service.files().export(fileId=fid, mimeType="text/plain").execute()
            else:
                return service.files().get_media(fileId=fid).execute()

        try:
            content = await loop.run_in_executor(None, _export)
            if isinstance(content, bytes):
                return content.decode("utf-8", errors="ignore")
            return str(content)
        except Exception as exc:
            logger.warning("Failed to download %s: %s", fid, exc)
            return ""
