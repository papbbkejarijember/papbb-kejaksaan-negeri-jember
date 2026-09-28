import hashlib
import hmac
import json
import os
from datetime import datetime, timezone

from fastapi import APIRouter, Header, HTTPException, Request, Response
from pymongo.errors import DuplicateKeyError

from lib.db import db


router = APIRouter()

EVENT_TO_STATUS = {
    "delivered": "delivered",
    "opened": "opened",
    "hardBounce": "hard_bounce",
    "hard_bounce": "hard_bounce",
    "softBounce": "soft_bounce",
    "soft_bounce": "soft_bounce",
    "blocked": "blocked",
    "error": "failed",
    "invalid": "invalid",
}
STATUS_RANK = {
    "simulated": 0,
    "submitted": 0,
    "soft_bounce": 1,
    "delivered": 2,
    "opened": 3,
    "failed": 4,
    "hard_bounce": 4,
    "blocked": 4,
    "invalid": 4,
}


def _event_key(payload: dict) -> str:
    raw = "|".join(
        str(payload.get(key, ""))
        for key in ("event", "message-id", "messageId", "ts_event", "ts", "email")
    )
    return hashlib.sha256(raw.encode()).hexdigest()


@router.post("/brevo", status_code=204)
async def brevo_webhook(request: Request, authorization: str | None = Header(default=None)):
    expected = os.environ.get("BREVO_WEBHOOK_TOKEN")
    supplied = authorization or ""
    if not expected or not hmac.compare_digest(supplied, f"Bearer {expected}"):
        raise HTTPException(status_code=401, detail="Webhook tidak terautentikasi")
    raw_body = await request.body()
    if len(raw_body) > 262_144:
        raise HTTPException(status_code=413, detail="Payload webhook terlalu besar")
    try:
        body = json.loads(raw_body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Payload webhook tidak valid")
    payloads = body if isinstance(body, list) else [body]
    for payload in payloads:
        if not isinstance(payload, dict):
            continue
        provider_event = str(payload.get("event", ""))
        status = EVENT_TO_STATUS.get(provider_event)
        message_id = payload.get("message-id") or payload.get("messageId")
        if not status or not message_id:
            continue
        received_at = datetime.now(timezone.utc).isoformat()
        try:
            await db.brevo_webhook_events.insert_one(
                {
                    "event_key": _event_key(payload),
                    "message_id": str(message_id),
                    "event": provider_event,
                    "status": status,
                    "received_at": received_at,
                }
            )
        except DuplicateKeyError:
            continue
        notification = await db.notifications.find_one(
            {"provider": "brevo", "provider_message_id": str(message_id)},
            {"status": 1},
        )
        if not notification:
            continue
        update: dict = {
            "$push": {
                "status_history": {
                    "status": status,
                    "provider_event": provider_event,
                    "at": received_at,
                    "provider_ts": payload.get("ts_event") or payload.get("ts"),
                }
            },
            "$set": {"updated_at": received_at},
        }
        current_status = notification.get("status", "submitted")
        if STATUS_RANK.get(status, 0) >= STATUS_RANK.get(current_status, 0):
            update["$set"]["status"] = status
        await db.notifications.update_one({"_id": notification["_id"]}, update)
    return Response(status_code=204)