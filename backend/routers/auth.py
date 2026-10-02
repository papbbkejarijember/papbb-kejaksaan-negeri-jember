from datetime import datetime, timedelta, timezone
import os
import uuid

from fastapi import APIRouter, HTTPException, Request, Response, status
from fastapi.responses import Response as ImageResponse
import base64
import binascii

from lib.audit import write_audit
from lib.auth import SESSION_COOKIE, get_current_user, hash_password, public_user, require_role, verify_password
from lib.db import db
from lib.email_service import send_email_notification
from lib.pii import decrypt_pii, encrypt_pii
from lib.rate_limit import clear_rate_limit, enforce_rate_limit
from models.auth import (
    AuditLog,
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



def _validate_ktp_image(value: str) -> str:
    if not value.startswith(("data:image/jpeg;base64,", "data:image/png;base64,", "data:image/webp;base64,")):
        raise HTTPException(status_code=422, detail="Berkas KTP harus berupa gambar JPG, PNG, atau WEBP")
    try:
        encoded = value.split(",", 1)[1]
        raw = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error, IndexError) as exc:
        raise HTTPException(status_code=422, detail="Data foto KTP tidak valid") from exc
    if len(raw) > 2_800_000:
        raise HTTPException(status_code=413, detail="Ukuran foto KTP terlalu besar. Maksimal 2,8 MB")
    if value.startswith("data:image/jpeg") and not raw.startswith(b"\\xff\\xd8\\xff"):
        raise HTTPException(status_code=422, detail="File JPEG tidak valid")
    if value.startswith("data:image/png") and not raw.startswith(b"\\x89PNG\\r\\n\\x1a\\n"):
        raise HTTPException(status_code=422, detail="File PNG tidak valid")
    if value.startswith("data:image/webp") and not (raw.startswith(b"RIFF") and raw[8:12] == b"WEBP"):
        raise HTTPException(status_code=422, detail="File WEBP tidak valid")
    return value

def _identity_response(document: dict) -> IdentitySubmission:
    clean = {key: value for key, value in document.items() if key != "_id"}
    clean["nik"] = decrypt_pii(clean.pop("nik_encrypted")) if clean.get("nik_encrypted") else clean.pop("nik", "")
    clean["address"] = decrypt_pii(clean.pop("address_encrypted")) if clean.get("address_encrypted") else clean.pop("address", "")
    has_image = bool(clean.pop("ktp_image_encrypted", None) or clean.pop("ktp_image_data", None))
    clean["ktp_image_url"] = f"/api/auth/verifications/{clean['id']}/image" if has_image else None
    return IdentitySubmission(**clean)


async def _start_session(user: dict, response: Response) -> SessionResponse:
    token = uuid.uuid4().hex + uuid.uuid4().hex
    expires_at = datetime.now(timezone.utc) + timedelta(hours=8)
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
        max_age=8 * 60 * 60,
        httponly=True,
        samesite="lax",
        secure=os.environ.get("COOKIE_SECURE", "true").lower() == "true",
        path="/",
    )
    return SessionResponse(user=public_user(user))


@router.post("/register", response_model=SessionResponse)
async def register(payload: RegisterRequest, response: Response, request: Request):
    await enforce_rate_limit(request, scope="register", limit=5, window_seconds=3600)
    if not payload.legal_consent:
        raise HTTPException(status_code=422, detail="Persetujuan kebijakan privasi dan syarat layanan wajib diberikan")
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
        "legal_consent_at": datetime.now(timezone.utc).isoformat(),
        "privacy_version": "2026-01",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.users.insert_one(user)
    await db.notification_preferences.insert_one(
        {"id": str(uuid.uuid4()), "user_id": user["id"], "email": True, "whatsapp": False}
    )
    return await _start_session(user, response)


@router.post("/identity", response_model=IdentitySubmission)
async def submit_identity(payload: IdentitySubmissionCreate, request: Request):
    user = await require_role(request, "participant")
    await enforce_rate_limit(request, scope="identity", identifier=user["id"], limit=5, window_seconds=3600)
    if not payload.consent:
        raise HTTPException(status_code=422, detail="Persetujuan pemrosesan KTP wajib diberikan")
    if not payload.nik.isdigit():
        raise HTTPException(status_code=422, detail="NIK harus terdiri dari 16 angka")
    _validate_ktp_image(payload.ktp_image_data)
    now = datetime.now(timezone.utc).isoformat()
    existing = await db.identity_verifications.find_one({"user_id": user["id"]})
    document = {
        "id": existing["id"] if existing else str(uuid.uuid4()),
        "user_id": user["id"],
        "full_name": user["full_name"],
        "email": user["email"],
        "nik_encrypted": encrypt_pii(payload.nik),
        "address_encrypted": encrypt_pii(payload.address.strip()),
        "ktp_image_encrypted": encrypt_pii(payload.ktp_image_data),
        "status": "pending",
        "submitted_at": now,
        "reviewed_at": None,
        "review_note": None,
        "consented_at": now,
    }
    await db.identity_verifications.replace_one({"user_id": user["id"]}, document, upsert=True)
    await db.users.update_one({"id": user["id"]}, {"$set": {"verification_status": "pending"}})
    return _identity_response(document)


@router.get("/verifications", response_model=list[IdentitySubmission])
async def list_verifications(request: Request):
    await require_role(request, "admin")
    documents = await db.identity_verifications.find().sort("submitted_at", -1).to_list(200)
    return [_identity_response(doc) for doc in documents]



@router.get("/verifications/{verification_id}/image")
async def verification_image(verification_id: str, request: Request):
    await require_role(request, "admin")
    document = await db.identity_verifications.find_one({"id": verification_id})
    if not document:
        raise HTTPException(status_code=404, detail="Pengajuan verifikasi tidak ditemukan")
    encrypted = document.get("ktp_image_encrypted") or document.get("ktp_image_data")
    if not encrypted:
        raise HTTPException(status_code=404, detail="Foto KTP tidak tersedia")
    value = decrypt_pii(encrypted) if document.get("ktp_image_encrypted") else encrypted
    try:
        header, encoded = value.split(",", 1)
        content = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error, IndexError) as exc:
        raise HTTPException(status_code=500, detail="Foto KTP rusak") from exc
    media_type = header.removeprefix("data:").removesuffix(";base64")
    return ImageResponse(content=content, media_type=media_type, headers={"Cache-Control": "private, no-store"})

@router.patch("/verifications/{verification_id}", response_model=IdentitySubmission)
async def review_verification(verification_id: str, payload: IdentityReviewRequest, request: Request):
    admin = await require_role(request, "admin")
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
    await write_audit(
        actor=admin, action=f"identity_{payload.status}", target_type="identity_verification",
        target_id=verification_id, request=request,
    )
    updated = await db.identity_verifications.find_one({"id": verification_id})
    return _identity_response(updated)


@router.delete("/verifications/{verification_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_verification(verification_id: str, request: Request):
    admin = await require_role(request, "admin")
    document = await db.identity_verifications.find_one({"id": verification_id})
    if not document:
        raise HTTPException(status_code=404, detail="Pengajuan verifikasi tidak ditemukan")
    await db.identity_verifications.delete_one({"id": verification_id})
    await db.users.update_one({"id": document["user_id"]}, {"$set": {"verification_status": "not_submitted"}})
    await write_audit(
        actor=admin, action="identity_deleted", target_type="identity_verification",
        target_id=verification_id, request=request,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/audit-logs", response_model=list[AuditLog])
async def list_audit_logs(request: Request):
    await require_role(request, "admin")
    documents = await db.audit_logs.find().sort("created_at", -1).to_list(100)
    return [AuditLog(**{key: value for key, value in doc.items() if key != "_id"}) for doc in documents]


@router.post("/login", response_model=SessionResponse)
async def login(payload: LoginRequest, response: Response, request: Request):
    email = _normalise_email(payload.email)
    rate_key = await enforce_rate_limit(request, scope="login", identifier=email, limit=5, window_seconds=900)
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(payload.password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Email atau kata sandi salah")
    await clear_rate_limit(rate_key)
    if not user.get("password_hash", "").startswith("pbkdf2_sha256$"):
        await db.users.update_one({"id": user["id"]}, {"$set": {"password_hash": hash_password(payload.password)}})
    await write_audit(actor=user, action="login_success", target_type="session", target_id=user["id"], request=request)
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
    response.delete_cookie(
        SESSION_COOKIE, path="/", secure=os.environ.get("COOKIE_SECURE", "true").lower() == "true", samesite="lax"
    )
    response.status_code = status.HTTP_204_NO_CONTENT
    return response
