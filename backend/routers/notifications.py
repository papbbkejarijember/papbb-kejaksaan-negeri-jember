import os

from fastapi import APIRouter, Request

from lib.auth import get_current_user
from lib.db import db
from lib.email_service import email_mode, record_mock_whatsapp, send_email_notification
from models.notification import Notification, NotificationConfig, NotificationTestCreate, NotificationTestResponse


router = APIRouter()


@router.get("/config", response_model=NotificationConfig)
async def notification_config():
    return NotificationConfig(
        email_mode=email_mode(),
        whatsapp_mode="mock",
        sender_email=os.environ.get("BREVO_SENDER_EMAIL"),
    )


@router.get("", response_model=list[Notification])
async def list_notifications(request: Request):
    user = await get_current_user(request)
    documents = await db.notifications.find({"user_id": user["id"]}).sort("created_at", -1).to_list(100)
    return [Notification(**{key: value for key, value in doc.items() if key != "_id"}) for doc in documents]


@router.post("/test", response_model=NotificationTestResponse)
async def test_notification(payload: NotificationTestCreate, request: Request):
    user = await get_current_user(request)
    created = []
    for channel in dict.fromkeys(payload.channels):
        if channel == "email":
            created.append(
                await send_email_notification(
                    user_id=user["id"], recipient=user["email"], subject=payload.subject,
                    message=payload.message, event="notification_test"
                )
            )
        else:
            created.append(
                await record_mock_whatsapp(
                    user_id=user["id"], subject=payload.subject, message=payload.message, event="notification_test"
                )
            )
    overall = "failed" if any(item.status == "failed" for item in created) else "submitted" if any(item.status == "submitted" for item in created) else "simulated"
    return NotificationTestResponse(status=overall, notifications=created)
