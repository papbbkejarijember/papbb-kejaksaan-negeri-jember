import hmac
import os
import uuid

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request, status
from pydantic import BaseModel
from pymongo.errors import DuplicateKeyError

from lib.backup import run_weekly_backup
from lib.db import db


router = APIRouter()


class CronEnvelope(BaseModel):
    event: str
    schedule_id: str | None = None
    run_id: str | None = None
    dispatch_time: str | None = None
    job_id: str | None = None
    data: None = None


@router.post("/weekly-backup", status_code=status.HTTP_202_ACCEPTED)
async def weekly_backup(
    payload: CronEnvelope,
    background_tasks: BackgroundTasks,
    authorization: str | None = Header(default=None),
    x_webhook_id: str | None = Header(default=None),
):
    # Cron endpoints must ack 2xx immediately; enqueue/background the actual work.
    expected = os.environ.get("WEBHOOK_CRON_SECRET", "")
    if not expected or not hmac.compare_digest(authorization or "", f"Bearer {expected}"):
        raise HTTPException(status_code=401, detail="Cron tidak terautentikasi")
    if payload.event != "schedule.triggered":
        raise HTTPException(status_code=400, detail="Envelope cron tidak valid")
    run_id = x_webhook_id or payload.run_id or str(uuid.uuid4())
    try:
        await db.cron_runs.insert_one({"run_id": run_id, "schedule_id": payload.schedule_id})
    except DuplicateKeyError:
        return {"accepted": True, "duplicate": True}
    background_tasks.add_task(run_weekly_backup, run_id)
    return {"accepted": True, "duplicate": False}
