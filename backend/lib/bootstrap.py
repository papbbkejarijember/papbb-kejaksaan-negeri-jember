import os
import uuid
from datetime import datetime, timezone

from lib.auth import hash_password
from lib.db import db


async def ensure_admin_account() -> None:
    email = os.environ.get("ADMIN_EMAIL", "").strip().lower()
    password = os.environ.get("ADMIN_BOOTSTRAP_PASSWORD", "")
    if not email or not password:
        return
    existing = await db.users.find_one({"email": email})
    if existing:
        await db.users.update_one({"id": existing["id"]}, {"$set": {"role": "admin", "verification_status": "approved"}})
        return
    await db.users.insert_one(
        {
            "id": str(uuid.uuid4()),
            "email": email,
            "full_name": "Administrator PAPPBB Kejari Jember",
            "role": "admin",
            "phone": None,
            "verification_status": "approved",
            "password_hash": hash_password(password),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    )