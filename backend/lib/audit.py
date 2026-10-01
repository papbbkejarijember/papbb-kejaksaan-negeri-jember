import hashlib
import hmac
import os
import uuid
from datetime import datetime, timezone

from fastapi import Request

from lib.db import db


def request_fingerprint(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    ip = forwarded.split(",")[0].strip() or (request.client.host if request.client else "unknown")
    salt = os.environ.get("AUDIT_HASH_SALT", "audit")
    return hmac.new(salt.encode(), ip.encode(), hashlib.sha256).hexdigest()[:20]


async def write_audit(
    *, actor: dict, action: str, target_type: str, target_id: str, request: Request,
    metadata: dict | None = None,
) -> None:
    await db.audit_logs.insert_one(
        {
            "id": str(uuid.uuid4()),
            "actor_id": actor["id"],
            "actor_role": actor.get("role", "unknown"),
            "action": action,
            "target_type": target_type,
            "target_id": target_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "metadata": {**(metadata or {}), "request_fingerprint": request_fingerprint(request)},
        }
    )