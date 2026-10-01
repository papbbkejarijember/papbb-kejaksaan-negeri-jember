import uuid

from conftest import pin_session_cookie


def test_registration_enforces_strong_password_and_legal_consent(client):
    email = f"tscheck-reg-{uuid.uuid4().hex[:10]}@example.com"

    # Weak password rejected even with consent
    r = client.post(
        "/auth/register",
        json={"full_name": "Tscheck Weak", "email": email, "password": "weak", "legal_consent": True},
    )
    assert r.status_code in (400, 422), (r.status_code, r.text[:300])

    # Strong password but no consent rejected
    r2 = client.post(
        "/auth/register",
        json={"full_name": "Tscheck NoConsent", "email": email, "password": "Strong@Test123", "legal_consent": False},
    )
    assert r2.status_code == 422, (r2.status_code, r2.text[:300])

    # Strong password + consent succeeds and starts a Secure session
    r3 = client.post(
        "/auth/register",
        json={"full_name": "Tscheck Participant", "email": email, "password": "Strong@Test123", "legal_consent": True},
    )
    assert r3.status_code == 200, (r3.status_code, r3.text[:300])
    set_cookie = r3.headers.get("set-cookie", "")
    assert "httponly" in set_cookie.lower() and "samesite=lax" in set_cookie.lower(), set_cookie
    pin_session_cookie(client, r3)
    me = client.get("/auth/me")
    assert me.status_code == 200 and me.json()["email"] == email
