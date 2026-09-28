from datetime import datetime, timedelta, timezone
import uuid

from fastapi import APIRouter, HTTPException, Request, Response, status

from lib.auth import SESSION_COOKIE, get_current_user, hash_password, public_user, verify_password
from lib.db import db
from models.auth import LoginRequest, RegisterRequest, SessionResponse, UserPublic


router = APIRouter()


def _normalise_email(value: str) -> str:
    return value.strip().lower()


async def _start_session(user: dict, response: Response) -> SessionResponse:
    token = uuid.uuid4().hex + uuid.uuid4().hex
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    await db.sessions.insert_one(
        {
            "id": str(uuid.uuid4()),
            "token": token,
            "user_id": user["id"],
            "expires_at": expires_at.isoformat(),
        }
    )
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=7 * 24 * 60 * 60,
        httponly=True,
        samesite="lax",
        path="/",
    )
    return SessionResponse(user=public_user(user))


@router.post("/register", response_model=SessionResponse)
async def register(payload: RegisterRequest, response: Response):
    email = _normalise_email(payload.email)
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=409, detail="Email sudah terdaftar")
    user = {
        "id": str(uuid.uuid4()),
        "email": email,
        "full_name": payload.full_name.strip(),
        "phone": payload.phone.strip() if payload.phone else None,
        "role": "participant",
        "password_hash": hash_password(payload.password),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.users.insert_one(user)
    await db.notification_preferences.insert_one(
        {"id": str(uuid.uuid4()), "user_id": user["id"], "email": True, "whatsapp": True}
    )
    return await _start_session(user, response)


@router.post("/login", response_model=SessionResponse)
async def login(payload: LoginRequest, response: Response):
    user = await db.users.find_one({"email": _normalise_email(payload.email)})
    if not user or not verify_password(payload.password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Email atau kata sandi salah")
    return await _start_session(user, response)


@router.get("/me", response_model=UserPublic | None)
async def me(request: Request):
    try:
        return public_user(await get_current_user(request))
    except HTTPException as exc:
        if exc.status_code == 401:
            return None
        raise


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(request: Request, response: Response):
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        await db.sessions.delete_one({"token": token})
    response.delete_cookie(SESSION_COOKIE, path="/")
    response.status_code = status.HTTP_204_NO_CONTENT
    return response
