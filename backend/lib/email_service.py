import html
import os
from datetime import datetime, timezone
import uuid

import httpx

from lib.db import db
from models.notification import Notification


BREVO_URL = "https://api.brevo.com/v3/smtp/email"


def email_mode() -> str:
    return "brevo" if os.environ.get("BREVO_API_KEY") and os.environ.get("BREVO_SENDER_EMAIL") else "mock"


async def send_email_notification(
    *,
    user_id: str,
    recipient: str,
    subject: str,
    message: str,
    event: str,
    auction_id: str | None = None,
) -> Notification:
    created_at = datetime.now(timezone.utc).isoformat()
    document = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "channel": "email",
        "subject": subject,
        "message": message,
        "status": "simulated",
        "provider": "mock",
        "provider_message_id": None,
        "event": event,
        "error": None,
        "auction_id": auction_id,
        "created_at": created_at,
        "updated_at": created_at,
    }
    if email_mode() == "brevo":
        payload = {
            "sender": {
                "name": os.environ.get("BREVO_SENDER_NAME", "Portal Lelang Kejaksaan Negeri Jember"),
                "email": os.environ["BREVO_SENDER_EMAIL"],
            },
            "to": [{"email": recipient}],
            "subject": subject,
            "htmlContent": (
                "<div style='font-family:Arial,sans-serif;line-height:1.6;color:#0f172a'>"
                "<h2 style='color:#0f2c59'>Portal Lelang Kejaksaan Negeri Jember</h2>"
                f"<p>{html.escape(message)}</p>"
                "<p style='font-size:12px;color:#64748b'>Pesan transaksional otomatis. Jangan membalas email ini.</p>"
                "</div>"
            ),
            "textContent": message,
        }
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "api-key": os.environ["BREVO_API_KEY"],
        }
        try:
            timeout = float(os.environ.get("BREVO_TIMEOUT_SECONDS", "10"))
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(BREVO_URL, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
            document["provider"] = "brevo"
            document["status"] = "submitted"
            document["provider_message_id"] = data.get("messageId") or (data.get("messageIds") or [None])[0]
        except httpx.HTTPStatusError as exc:
            document["provider"] = "brevo"
            document["status"] = "failed"
            document["error"] = f"HTTP {exc.response.status_code}"
        except (httpx.HTTPError, ValueError) as exc:
            document["provider"] = "brevo"
            document["status"] = "failed"
            document["error"] = type(exc).__name__
    document["status_history"] = [
        {"status": document["status"], "provider_event": None, "at": created_at, "provider_ts": None}
    ]
    await db.notifications.insert_one(document)
    return Notification(**document)


async def record_mock_whatsapp(
    *, user_id: str, subject: str, message: str, event: str, auction_id: str | None = None
) -> Notification | None:
    if os.environ.get("WHATSAPP_ENABLED", "false").lower() != "true":
        return None
    created_at = datetime.now(timezone.utc).isoformat()
    document = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "channel": "whatsapp",
        "subject": subject,
        "message": message,
        "status": "simulated",
        "provider": "mock",
        "provider_message_id": None,
        "event": event,
        "error": None,
        "auction_id": auction_id,
        "created_at": created_at,
        "updated_at": created_at,
        "status_history": [
            {"status": "simulated", "provider_event": None, "at": created_at, "provider_ts": None}
        ],
    }
    await db.notifications.insert_one(document)
    return Notification(**document)