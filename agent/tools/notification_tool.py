"""
Notification tools – Phase 4.
  • EmailNotifier  – sends emails via SMTP (aiosmtplib)
  • WebhookTrigger – fires HTTP POST webhooks
"""

import logging
from typing import Any, Dict

import httpx

from settings import settings

logger = logging.getLogger(__name__)


class EmailNotifier:
    async def send(self, to: str, subject: str, body: str) -> Dict[str, Any]:
        if not settings.smtp_username:
            logger.warning("SMTP not configured – email skipped")
            return {"status": "skipped", "reason": "SMTP not configured"}

        try:
            import aiosmtplib
            from email.message import EmailMessage

            msg = EmailMessage()
            msg["From"] = settings.smtp_username
            msg["To"] = to
            msg["Subject"] = subject
            msg.set_content(body)

            await aiosmtplib.send(
                msg,
                hostname=settings.smtp_host,
                port=settings.smtp_port,
                username=settings.smtp_username,
                password=settings.smtp_password,
                start_tls=True,
            )
            logger.info("Email sent to %s", to)
            return {"status": "sent", "to": to}
        except Exception as exc:
            logger.error("Email send failed: %s", exc)
            return {"status": "error", "error": str(exc)}


class WebhookTrigger:
    async def post(self, url: str, data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(url, json=data)
                resp.raise_for_status()
            logger.info("Webhook triggered: %s → %s", url, resp.status_code)
            return {"status": "triggered", "http_status": resp.status_code}
        except Exception as exc:
            logger.error("Webhook failed: %s", exc)
            return {"status": "error", "error": str(exc)}
