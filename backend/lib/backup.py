import asyncio
import os
import tempfile
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import boto3
from cryptography.fernet import Fernet

from lib.db import db


def backup_configured() -> bool:
    required = (
        "BACKUP_S3_BUCKET", "BACKUP_S3_REGION", "BACKUP_S3_ACCESS_KEY_ID",
        "BACKUP_S3_SECRET_ACCESS_KEY", "BACKUP_ENCRYPTION_KEY",
    )
    return os.environ.get("BACKUP_ENABLED", "false").lower() == "true" and all(os.environ.get(key) for key in required)


async def run_weekly_backup(run_id: str) -> None:
    created_at = datetime.now(timezone.utc)
    record = {
        "id": str(uuid.uuid4()),
        "run_id": run_id,
        "status": "skipped" if not backup_configured() else "running",
        "created_at": created_at.isoformat(),
        "completed_at": None,
        "object_key": None,
        "error": None,
    }
    await db.backup_runs.insert_one(record)
    if not backup_configured():
        await db.backup_runs.update_one({"id": record["id"]}, {"$set": {"completed_at": datetime.now(timezone.utc).isoformat(), "error": "S3 credentials not configured"}})
        return
    try:
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "mongo.archive.gz"
            process = await asyncio.create_subprocess_exec(
                "mongodump", f"--uri={os.environ['MONGO_URL']}", f"--db={os.environ['DB_NAME']}",
                f"--archive={archive}", "--gzip",
                stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await process.communicate()
            if process.returncode != 0:
                raise RuntimeError(f"mongodump failed ({process.returncode})")
            encrypted = Fernet(os.environ["BACKUP_ENCRYPTION_KEY"].encode()).encrypt(archive.read_bytes())
        key = f"portal-lelang-kejari-jember/backups/{created_at.strftime('%Y/%m/%d')}/{run_id}.archive.gz.enc"
        client = boto3.client(
            "s3",
            region_name=os.environ["BACKUP_S3_REGION"],
            aws_access_key_id=os.environ["BACKUP_S3_ACCESS_KEY_ID"],
            aws_secret_access_key=os.environ["BACKUP_S3_SECRET_ACCESS_KEY"],
            endpoint_url=os.environ.get("BACKUP_S3_ENDPOINT_URL") or None,
        )
        await asyncio.to_thread(
            client.put_object,
            Bucket=os.environ["BACKUP_S3_BUCKET"], Key=key, Body=encrypted,
            ContentType="application/octet-stream", ServerSideEncryption="AES256",
        )
        cutoff = created_at - timedelta(days=int(os.environ.get("BACKUP_RETENTION_DAYS", "90")))
        response = await asyncio.to_thread(
            client.list_objects_v2,
            Bucket=os.environ["BACKUP_S3_BUCKET"], Prefix="portal-lelang-kejari-jember/backups/",
        )
        expired = [{"Key": item["Key"]} for item in response.get("Contents", []) if item["LastModified"] < cutoff]
        if expired:
            await asyncio.to_thread(client.delete_objects, Bucket=os.environ["BACKUP_S3_BUCKET"], Delete={"Objects": expired})
        await db.backup_runs.update_one({"id": record["id"]}, {"$set": {"status": "completed", "completed_at": datetime.now(timezone.utc).isoformat(), "object_key": key}})
    except Exception as exc:
        await db.backup_runs.update_one({"id": record["id"]}, {"$set": {"status": "failed", "completed_at": datetime.now(timezone.utc).isoformat(), "error": type(exc).__name__}})
