import os
from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Query, Request, Response

from lib.auth import get_current_user, require_role
from lib.db import db
from lib.email_service import email_mode, record_mock_whatsapp, send_email_notification
from lib.email_analytics_export import build_analytics_csv, build_analytics_pdf
from models.notification import (
    Notification,
    EmailAnalytics,
    EmailAnalyticsPoint,
    EmailAnalyticsTotals,
    NotificationConfig,
    NotificationHistoryResponse,
    NotificationTestCreate,
    NotificationTestResponse,
)


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


@router.get("/analytics/email", response_model=EmailAnalytics)
async def email_analytics(
    request: Request,
    period: str = Query(default="30d", alias="range", pattern="^(7d|30d|all)$"),
):
    await require_role(request, "admin")
    now = datetime.now(timezone.utc)
    days = 7 if period == "7d" else 30 if period == "30d" else None
    start = (now - timedelta(days=days - 1)).replace(hour=0, minute=0, second=0, microsecond=0) if days else None
    query: dict = {"provider": "brevo", "channel": "email"}
    if start:
        query["created_at"] = {"$gte": start.isoformat()}
    documents = await db.notifications.find(
        query,
        {"status": 1, "status_history": 1, "created_at": 1},
    ).sort("created_at", 1).to_list(10000)
    failed_statuses = {"soft_bounce", "hard_bounce", "blocked", "invalid", "failed"}
    totals = {"sent": len(documents), "delivered": 0, "opened": 0, "failed": 0}
    daily: dict[str, dict[str, int]] = {}
    if start:
        for offset in range(days or 0):
            date = (start + timedelta(days=offset)).date().isoformat()
            daily[date] = {"sent": 0, "delivered": 0, "opened": 0, "failed": 0}
    for document in documents:
        date = str(document.get("created_at", now.isoformat()))[:10]
        daily.setdefault(date, {"sent": 0, "delivered": 0, "opened": 0, "failed": 0})
        daily[date]["sent"] += 1
        statuses = {str(item.get("status")) for item in document.get("status_history", [])}
        statuses.add(str(document.get("status", "submitted")))
        delivered = bool(statuses & {"delivered", "opened"})
        opened = "opened" in statuses
        failed = bool(statuses & failed_statuses)
        if delivered:
            totals["delivered"] += 1
            daily[date]["delivered"] += 1
        if opened:
            totals["opened"] += 1
            daily[date]["opened"] += 1
        if failed:
            totals["failed"] += 1
            daily[date]["failed"] += 1
    sent = totals["sent"]
    delivered_count = totals["delivered"]
    return EmailAnalytics(
        range=period,
        from_date=start.date().isoformat() if start else (min(daily) if daily else None),
        to_date=now.date().isoformat(),
        totals=EmailAnalyticsTotals(**totals),
        delivery_rate=round((totals["delivered"] / sent * 100) if sent else 0, 1),
        open_rate=round((totals["opened"] / delivered_count * 100) if delivered_count else 0, 1),
        failure_rate=round((totals["failed"] / sent * 100) if sent else 0, 1),
        trend=[EmailAnalyticsPoint(date=date, **values) for date, values in sorted(daily.items())],
    )


@router.get("/analytics/email/export")
async def export_email_analytics(
    request: Request,
    period: str = Query(default="30d", alias="range", pattern="^(7d|30d|all)$"),
    format: Literal["csv", "pdf"] = Query(default="csv"),
):
    analytics = await email_analytics(request=request, period=period)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    filename = f"analitik-email-{period}-{stamp}.{format}"
    if format == "csv":
        content = build_analytics_csv(analytics)
        media_type = "text/csv; charset=utf-8"
    else:
        content = await build_analytics_pdf(analytics)
        media_type = "application/pdf"
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{notification_id}/status-history", response_model=NotificationHistoryResponse)
async def notification_status_history(notification_id: str, request: Request):
    user = await get_current_user(request)
    document = await db.notifications.find_one({"id": notification_id, "user_id": user["id"]})
    if not document:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Riwayat notifikasi tidak ditemukan")
    return NotificationHistoryResponse(status=document["status"], history=document.get("status_history", []))


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
