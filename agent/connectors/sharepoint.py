"""
SharePoint connector.

Supports a lightweight mock mode for portfolio demos and a minimal Microsoft
Graph path when a bearer token plus drive identifiers are supplied.
"""

import logging
from typing import Any, Dict, List

import httpx

from ingestion.pipeline import ConnectorIngestionPipeline
from settings import settings

logger = logging.getLogger(__name__)


class SharePointConnector:
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
          mock (optional) - true to use supplied/mock documents
          documents (optional) - list of {id, title, text, metadata}
          site_id, drive_id, folder_item_id - optional Microsoft Graph targets
          max_files - max files to pull from Graph
        """
        if params.get("documents"):
            return [self._from_mock_doc(doc) for doc in params["documents"]]

        mock_param = params.get("mock")
        use_mock = (
            getattr(settings, "sharepoint_mock_enabled", True)
            if mock_param is None
            else bool(mock_param)
        )
        if use_mock:
            logger.info("SharePoint mock ingestion enabled for user %s", user_id)
            return [self._demo_test_report()]

        token = getattr(settings, "microsoft_graph_token", "")
        site_id = params.get("site_id") or getattr(settings, "sharepoint_site_id", "")
        drive_id = params.get("drive_id") or getattr(
            settings, "sharepoint_drive_id", ""
        )
        if not token or not site_id or not drive_id:
            logger.warning("SharePoint Graph not configured; no documents pulled")
            return []

        folder_item_id = params.get("folder_item_id", "root")
        max_files = int(params.get("max_files", 10))
        return await self._fetch_graph_documents(
            token, site_id, drive_id, folder_item_id, max_files
        )

    @staticmethod
    def _from_mock_doc(doc: Dict[str, Any]) -> Dict[str, Any]:
        title = str(
            doc.get("title")
            or doc.get("name")
            or doc.get("id")
            or "SharePoint document"
        )
        return {
            "source": "sharepoint",
            "external_id": str(doc.get("id") or title),
            "title": title,
            "text": str(doc.get("text") or ""),
            "metadata": dict(doc.get("metadata") or {}),
        }

    @staticmethod
    def _demo_test_report() -> Dict[str, Any]:
        text = (
            "EV Battery Pack Validation Test Report\n"
            "Test ID: EVT-24-118\n"
            "Issue: Thermal cycling test failed after 42 cycles. The pack reported "
            "intermittent voltage drops on module B and insulation resistance below "
            "the acceptance threshold.\n"
            "Containment: Stop shipment for affected lot L-2024-17 and quarantine "
            "modules assembled between May 02 and May 05.\n"
            "Root cause evidence: Microscopy found solder voids on the sense harness "
            "connector. Process logs show reflow oven zone 4 temperature drifted "
            "12C below specification during the affected build window.\n"
            "Corrective action: Recalibrate oven zone 4, add SPC alerting for zone "
            "temperature drift, and add AOI inspection for sense harness solder joints.\n"
            "Verification: Repeat 100 thermal cycles and insulation resistance test "
            "on three consecutive production lots with zero failures."
        )
        return {
            "source": "sharepoint",
            "external_id": "mock_evt_24_118",
            "title": "SharePoint Mock - EV Battery Pack Validation Test Report",
            "text": text,
            "metadata": {
                "mock": True,
                "system": "sharepoint",
                "document_type": "test_report",
            },
        }

    async def _fetch_graph_documents(
        self,
        token: str,
        site_id: str,
        drive_id: str,
        folder_item_id: str,
        max_files: int,
    ) -> List[Dict[str, Any]]:
        headers = {"Authorization": f"Bearer {token}"}
        base = "https://graph.microsoft.com/v1.0"
        if folder_item_id == "root":
            list_url = f"{base}/sites/{site_id}/drives/{drive_id}/root/children"
        else:
            list_url = f"{base}/sites/{site_id}/drives/{drive_id}/items/{folder_item_id}/children"

        documents: List[Dict[str, Any]] = []
        async with httpx.AsyncClient(timeout=30) as client:
            list_resp = await client.get(
                list_url, headers=headers, params={"$top": max_files}
            )
            list_resp.raise_for_status()
            for item in list_resp.json().get("value", [])[:max_files]:
                if "file" not in item:
                    continue
                download_url = item.get("@microsoft.graph.downloadUrl")
                if not download_url:
                    continue
                content_resp = await client.get(download_url)
                content_resp.raise_for_status()
                text = content_resp.content.decode("utf-8", errors="ignore")
                if not text.strip():
                    continue
                documents.append(
                    {
                        "source": "sharepoint",
                        "external_id": item.get("id", item.get("name", "")),
                        "title": item.get("name", "SharePoint document"),
                        "text": text,
                        "metadata": {
                            "web_url": item.get("webUrl", ""),
                            "mime_type": item.get("file", {}).get("mimeType", ""),
                        },
                    }
                )
        logger.info("SharePoint Graph pulled %d documents", len(documents))
        return documents
