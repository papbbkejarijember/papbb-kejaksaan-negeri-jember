import hashlib
import hmac
import secrets
from datetime import datetime, timezone

from fastapi import HTTPException, Request

from lib.db import db
from models.auth import Role, UserPublic


SESSION_COOKIE = "kejari_session"


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120_000).hex()
    return f"{salt}${digest}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        salt, expected = encoded.split("$", 1)
    except ValueError:
        return False
    actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120_000).hex()
    return hmac.compare_digest(actual, expected)


def public_user(doc: dict) -> UserPublic:
    return UserPublic(
        id=str(doc["id"]),
        email=doc["email"],
        full_name=doc["full_name"],
        role=doc["role"],
        phone=doc.get("phone"),
        verification_status=doc.get("verification_status", "approved" if doc.get("role") == "admin" else "not_submitted"),
        created_at=doc["created_at"],
    )


async def get_current_user(request: Request) -> dict:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise HTTPException(status_code=401, detail="Sesi login tidak ditemukan")
    session = await db.sessions.find_one({"token": token})
    if not session:
        raise HTTPException(status_code=401, detail="Sesi login tidak valid")
    try:
        expires_at = datetime.fromisoformat(session["expires_at"])
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
    except (KeyError, ValueError):
        raise HTTPException(status_code=401, detail="Sesi login rusak")
    if expires_at <= datetime.now(timezone.utc):
        await db.sessions.delete_one({"token": token})
        raise HTTPException(status_code=401, detail="Sesi login telah berakhir")
    user = await db.users.find_one({"id": session["user_id"]})
    if not user:
        raise HTTPException(status_code=401, detail="Akun tidak ditemukan")
    return user


async def require_role(request: Request, role: Role) -> dict:
    user = await get_current_user(request)
    if user.get("role") != role:
        raise HTTPException(status_code=403, detail="Akses ini hanya untuk peran tertentu")
    return user
