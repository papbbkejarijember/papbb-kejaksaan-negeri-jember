import asyncio
import os

from lib.auth import hash_password
from lib.bootstrap import ensure_admin_account
from lib.db import client, db, ensure_indexes
from lib.pii import encrypt_pii


async def main():
    await ensure_admin_account()
    email = os.environ.get("ADMIN_EMAIL", "").strip().lower()
    password = os.environ.get("ADMIN_BOOTSTRAP_PASSWORD", "")
    if email and password:
        admin = await db.users.find_one({"email": email})
        if admin:
            await db.users.update_one(
                {"id": admin["id"]},
                {"$set": {"password_hash": hash_password(password), "role": "admin", "verification_status": "approved"}},
            )
    await db.users.delete_many({"email": {"$in": ["admin@kejari-jember.go.id", "peserta@kejari-jember.go.id"]}})
    async for document in db.identity_verifications.find({"nik": {"$exists": True}}):
        await db.identity_verifications.update_one(
            {"_id": document["_id"]},
            {
                "$set": {
                    "nik_encrypted": encrypt_pii(document["nik"]),
                    "address_encrypted": encrypt_pii(document.get("address", "")),
                    "ktp_image_encrypted": encrypt_pii(document.get("ktp_image_data", "")),
                },
                "$unset": {"nik": "", "address": "", "ktp_image_data": ""},
            },
        )
    await db.sessions.delete_many({})
    await ensure_indexes()
    client.close()


if __name__ == "__main__":
    asyncio.run(main())