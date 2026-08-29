"""
Smart Document Chatbot — batch document ingestion DAG.

Runs on a schedule (default daily 02:00) to pull documents dropped into the
shared ``inbound/`` volume and push them through the Spring Boot ingestion
endpoint (parse -> chunk -> embed -> index into PostgreSQL chunks).

Design notes (honest):
- The core chat path uses PostgreSQL lexical chunks; this DAG feeds that path by
  calling the real backend upload API, not the experimental Qdrant agent path.
- Auth uses a JWT obtained from the backend login endpoint; credentials come from
  Airflow Variables / Connections (never hardcoded).
- If the backend is unreachable the task fails fast and Airflow retries per the
  ``retries`` policy below; poisoned files are skipped and reported, not fatal.

Required Airflow Variables / Connections:
  - Connection ``smartdoc_backend`` (HTTP)  -> backend base URL (e.g. http://backend:8080)
  - Variable   ``smartdoc_ingest_owner``     -> owner username for uploaded docs
  - Variable   ``smartdoc_ingest_inbound``   -> mounted dir to scan (default /opt/airflow/inbound)
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta

import requests
from airflow.decorators import dag, task
from airflow.models.connection import Connection
from airflow.models.variable import Variable

DEFAULT_INBOUND = "/opt/airflow/inbound"
SUPPORTED_EXT = (".pdf", ".docx", ".txt", ".md")


def _backend_base_url() -> str:
    conn = Connection.get_connection_from_secrets("smartdoc_backend")
    return (conn.get_uri() if hasattr(conn, "get_uri") else None) or os.environ.get(
        "SMARTDOC_BACKEND_URL", "http://backend:8080"
    )


def _login(base_url: str, owner: str) -> str:
    """Obtain a JWT for the ingestion owner via the real auth endpoint."""
    username = os.environ.get("SMARTDOC_INGEST_USERNAME") or owner
    password = os.environ.get("SMARTDOC_INGEST_PASSWORD", "")
    resp = requests.post(
        f"{base_url}/api/auth/login",
        json={"username": username, "password": password},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["token"]


def _csrf_token(base_url: str, token: str) -> str:
    resp = requests.get(
        f"{base_url}/api/csrf",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json().get("token", "")


@dag(
    dag_id="document_ingestion_pipeline",
    description="Batch ingest documents from the inbound volume into the RAG backend.",
    schedule="0 2 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,
    default_args={
        "owner": "data-platform",
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
        "execution_timeout": timedelta(hours=1),
    },
    tags=["rag", "ingestion", "smart-doc-chatbot"],
)
def document_ingestion_pipeline() -> None:
    @task
    def discover_files() -> list[str]:
        """List supported files present in the inbound directory."""
        inbound = Variable.get("smartdoc_ingest_inbound", DEFAULT_INBOUND)
        if not os.path.isdir(inbound):
            return []
        files = [
            os.path.join(inbound, f)
            for f in os.listdir(inbound)
            if f.lower().endswith(SUPPORTED_EXT)
        ]
        return files

    @task
    def ingest_file(path: str) -> dict:
        """Upload one file through the backend ingestion API."""
        base_url = _backend_base_url()
        owner = Variable.get("smartdoc_ingest_owner", "airflow-bot")
        token = _login(base_url, owner)
        csrf = _csrf_token(base_url, token)

        with open(path, "rb") as fh:
            resp = requests.post(
                f"{base_url}/api/documents/upload",
                headers={
                    "Authorization": f"Bearer {token}",
                    "X-XSRF-TOKEN": csrf,
                },
                files={"file": (os.path.basename(path), fh)},
                timeout=180,
            )
        if resp.status_code >= 400:
            return {"file": path, "status": "failed", "http": resp.status_code}
        body = resp.json()
        # Move processed file out of the inbound dir so it is not re-ingested.
        done_dir = os.path.join(os.path.dirname(path), "processed")
        os.makedirs(done_dir, exist_ok=True)
        os.replace(path, os.path.join(done_dir, os.path.basename(path)))
        return {
            "file": path,
            "status": "uploaded" if body.get("success") else "failed",
            "documentId": body.get("documentId"),
        }

    @task
    def summarize(results: list[dict]) -> dict:
        ok = sum(1 for r in results if r.get("status") == "uploaded")
        failed = [r["file"] for r in results if r.get("status") != "uploaded"]
        return {"total": len(results), "uploaded": ok, "failed": failed}

    files = discover_files()
    summary = summarize(ingest_file.expand(path=files))
    files >> summary


document_ingestion_pipeline()
