from datetime import datetime, timedelta, timezone
import uuid

from fastapi import APIRouter, HTTPException, Request, Response, status

from lib.auth import SESSION_COOKIE, get_current_user, hash_password, public_user, require_role, verify_password
from lib.db import db
from lib.email_service import send_email_notification
from models.auth import (
    IdentityReviewRequest,
    IdentitySubmission,
    IdentitySubmissionCreate,
    LoginRequest,
    RegisterRequest,
    SessionResponse,
    UserPublic,
)


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
        "verification_status": "not_submitted",
        "password_hash": hash_password(payload.password),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.users.insert_one(user)
    await db.notification_preferences.insert_one(
        {"id": str(uuid.uuid4()), "user_id": user["id"], "email": True, "whatsapp": True}
    )
    return await _start_session(user, response)


@router.post("/identity", response_model=IdentitySubmission)
async def submit_identity(payload: IdentitySubmissionCreate, request: Request):
    user = await require_role(request, "participant")
    if not payload.nik.isdigit():
        raise HTTPException(status_code=422, detail="NIK harus terdiri dari 16 angka")
    if not payload.ktp_image_data.startswith(("data:image/jpeg;base64,", "data:image/png;base64,", "data:image/webp;base64,")):
        raise HTTPException(status_code=422, detail="Berkas KTP harus berupa gambar JPG, PNG, atau WEBP")
    now = datetime.now(timezone.utc).isoformat()
    existing = await db.identity_verifications.find_one({"user_id": user["id"]})
    document = {
        "id": existing["id"] if existing else str(uuid.uuid4()),
        "user_id": user["id"],
        "full_name": user["full_name"],
        "email": user["email"],
        "nik": payload.nik,
        "address": payload.address.strip(),
        "ktp_image_data": payload.ktp_image_data,
        "status": "pending",
        "submitted_at": now,
        "reviewed_at": None,
        "review_note": None,
    }
    await db.identity_verifications.replace_one({"user_id": user["id"]}, document, upsert=True)
    await db.users.update_one({"id": user["id"]}, {"$set": {"verification_status": "pending"}})
    return IdentitySubmission(**document)


@router.get("/verifications", response_model=list[IdentitySubmission])
async def list_verifications(request: Request):
    await require_role(request, "admin")
    documents = await db.identity_verifications.find().sort("submitted_at", -1).to_list(200)
    return [IdentitySubmission(**{key: value for key, value in doc.items() if key != "_id"}) for doc in documents]


@router.patch("/verifications/{verification_id}", response_model=IdentitySubmission)
async def review_verification(verification_id: str, payload: IdentityReviewRequest, request: Request):
    await require_role(request, "admin")
    document = await db.identity_verifications.find_one({"id": verification_id})
    if not document:
        raise HTTPException(status_code=404, detail="Pengajuan verifikasi tidak ditemukan")
    reviewed_at = datetime.now(timezone.utc).isoformat()
    await db.identity_verifications.update_one(
        {"id": verification_id},
        {"$set": {"status": payload.status, "reviewed_at": reviewed_at, "review_note": payload.review_note}},
    )
    await db.users.update_one({"id": document["user_id"]}, {"$set": {"verification_status": payload.status}})
    subject = "Verifikasi identitas disetujui" if payload.status == "approved" else "Verifikasi identitas perlu diperbaiki"
    message = (
        "Identitas Anda telah disetujui. Anda sekarang dapat mengikuti penawaran lelang."
        if payload.status == "approved"
        else f"Pengajuan identitas ditolak. Catatan petugas: {payload.review_note or 'Silakan unggah ulang dokumen yang jelas.'}"
    )
    await send_email_notification(
        user_id=document["user_id"], recipient=document["email"], subject=subject, message=message, event="identity_review"
    )
    updated = await db.identity_verifications.find_one({"id": verification_id})
    return IdentitySubmission(**{key: value for key, value in updated.items() if key != "_id"})


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
