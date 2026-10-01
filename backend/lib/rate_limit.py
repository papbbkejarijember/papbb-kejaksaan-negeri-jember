import hashlib
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, Request

from lib.audit import request_fingerprint
from lib.db import db


async def enforce_rate_limit(
    request: Request, *, scope: str, identifier: str = "", limit: int, window_seconds: int
) -> str:
    fingerprint = request_fingerprint(request)
    digest = hashlib.sha256(f"{scope}:{fingerprint}:{identifier.lower()}".encode()).hexdigest()
    now = datetime.now(timezone.utc)
    document = await db.rate_limits.find_one({"key": digest})
    expires_at = document.get("expires_at") if document else None
    if expires_at and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if document and expires_at and expires_at > now:
        if document.get("count", 0) >= limit:
            raise HTTPException(status_code=429, detail="Terlalu banyak percobaan. Silakan coba kembali nanti")
        await db.rate_limits.update_one({"key": digest}, {"$inc": {"count": 1}})
    else:
        await db.rate_limits.replace_one(
            {"key": digest},
            {"key": digest, "count": 1, "expires_at": now + timedelta(seconds=window_seconds)},
            upsert=True,
        )
    return digest


async def clear_rate_limit(key: str) -> None:
    await db.rate_limits.delete_one({"key": key})