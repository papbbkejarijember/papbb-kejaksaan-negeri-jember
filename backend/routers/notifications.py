import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Request

from lib.auth import get_current_user
from lib.db import db
from models.notification import Notification, NotificationTestCreate, NotificationTestResponse


router = APIRouter()


@router.get("", response_model=list[Notification])
async def list_notifications(request: Request):
    user = await get_current_user(request)
    documents = await db.notifications.find({"user_id": user["id"]}).sort("created_at", -1).to_list(100)
    return [Notification(**{key: value for key, value in doc.items() if key != "_id"}) for doc in documents]


@router.post("/test", response_model=NotificationTestResponse)
async def test_notification(payload: NotificationTestCreate, request: Request):
    user = await get_current_user(request)
    created_at = datetime.now(timezone.utc).isoformat()
    created = []
    for channel in dict.fromkeys(payload.channels):
        document = {
            "id": str(uuid.uuid4()),
            "user_id": user["id"],
            "channel": channel,
            "subject": payload.subject,
            "message": payload.message,
            "status": "simulated",
            "provider": "mock",
            "created_at": created_at,
        }
        await db.notifications.insert_one(document)
        created.append(Notification(**document))
    return NotificationTestResponse(status="simulated", notifications=created)
