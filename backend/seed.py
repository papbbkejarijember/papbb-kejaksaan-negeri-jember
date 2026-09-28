import asyncio
from datetime import datetime, timezone
import uuid

from lib.auth import hash_password
from lib.db import client, db, ensure_indexes


ACCOUNTS = [
    {
        "email": "admin@kejari-jember.go.id",
        "full_name": "Admin Kejari Jember",
        "role": "admin",
        "password": "AdminJember123!",
        "phone": "6281234567890",
        "verification_status": "approved",
    },
    {
        "email": "peserta@kejari-jember.go.id",
        "full_name": "Peserta Demo Jember",
        "role": "participant",
        "password": "PesertaJember123!",
        "phone": "6281234567891",
        "verification_status": "approved",
    },
]


async def main():
    for account in ACCOUNTS:
        existing = await db.users.find_one({"email": account["email"]})
        if existing:
            await db.users.update_one(
                {"email": account["email"]},
                {"$set": {"role": account["role"], "verification_status": account["verification_status"]}},
            )
            continue
        user = {
            "id": str(uuid.uuid4()),
            "email": account["email"],
            "full_name": account["full_name"],
            "role": account["role"],
            "phone": account["phone"],
            "verification_status": account["verification_status"],
            "password_hash": hash_password(account["password"]),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        await db.users.insert_one(user)
        await db.notification_preferences.insert_one(
            {"id": str(uuid.uuid4()), "user_id": user["id"], "email": True, "whatsapp": True}
        )
    await ensure_indexes()
    client.close()


if __name__ == "__main__":
    asyncio.run(main())