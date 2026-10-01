import base64
import os
import uuid

import pymongo

from conftest import login_as, pin_session_cookie

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "app")
ADMIN_EMAIL = "pbrkejarijember@gmail.com"
ADMIN_PASSWORD = "@Papbbjember1234"

TINY_PNG_B64 = base64.b64encode(bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108020000009077"
    "53de0000000c4944415478da6360000002000155037dc80000000049454e44ae426082"
)).decode()


def test_identity_verification_consent_encryption_and_admin_lifecycle(client):
    suffix = uuid.uuid4().hex[:10]
    nik = "3301" + uuid.uuid4().hex[:12].replace("a", "1").replace("b", "2")[:12].ljust(12, "9")
    nik = "".join(c if c.isdigit() else "7" for c in nik)[:16].ljust(16, "1")
    email = f"tscheck-ktp-{suffix}@example.com"

    r = client.post(
        "/auth/register",
        json={"full_name": "Tscheck KTP Peserta", "email": email, "password": "Strong@Test123", "legal_consent": True},
    )
    assert r.status_code == 200, (r.status_code, r.text[:300])
    pin_session_cookie(client, r)
    user_id = client.get("/auth/me").json()["id"]

    # Missing consent rejected
    r_no_consent = client.post(
        "/auth/identity",
        json={
            "nik": nik, "address": f"Jl. Tscheck No. {suffix}",
            "ktp_image_data": f"data:image/png;base64,{TINY_PNG_B64}", "consent": False,
        },
    )
    assert r_no_consent.status_code == 422, (r_no_consent.status_code, r_no_consent.text[:300])

    # Valid submission with consent succeeds
    r_submit = client.post(
        "/auth/identity",
        json={
            "nik": nik, "address": f"Jl. Tscheck No. {suffix}",
            "ktp_image_data": f"data:image/png;base64,{TINY_PNG_B64}", "consent": True,
        },
    )
    assert r_submit.status_code == 200, (r_submit.status_code, r_submit.text[:300])
    submitted = r_submit.json()
    assert submitted["nik"] == nik
    verification_id = submitted["id"]

    # DB must never store plaintext PII fields
    mongo = pymongo.MongoClient(MONGO_URL)
    try:
        doc = mongo[DB_NAME].identity_verifications.find_one({"id": verification_id})
        assert doc is not None
        assert "nik" not in doc and "address" not in doc and "ktp_image_data" not in doc
        assert doc.get("nik_encrypted") and nik not in doc["nik_encrypted"]
        assert doc.get("address_encrypted")
        assert doc.get("ktp_image_encrypted") and TINY_PNG_B64 not in doc["ktp_image_encrypted"]
    finally:
        mongo.close()

    client.post("/auth/logout")
    admin_login = login_as(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    assert admin_login.status_code == 200, (admin_login.status_code, admin_login.text[:300])

    listing = client.get("/auth/verifications")
    assert listing.status_code == 200
    match = next((v for v in listing.json() if v["id"] == verification_id), None)
    assert match is not None and match["nik"] == nik and match["address"] == f"Jl. Tscheck No. {suffix}"

    approve = client.patch(f"/auth/verifications/{verification_id}", json={"status": "approved"})
    assert approve.status_code == 200, (approve.status_code, approve.text[:300])
    assert approve.json()["status"] == "approved"

    delete = client.delete(f"/auth/verifications/{verification_id}")
    assert delete.status_code == 204, (delete.status_code, delete.text[:300])

    listing_after = client.get("/auth/verifications")
    assert all(v["id"] != verification_id for v in listing_after.json())
