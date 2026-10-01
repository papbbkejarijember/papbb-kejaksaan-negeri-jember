import uuid

import httpx

from conftest import API_URL


def test_login_rate_limit_cors_cookie_and_security_headers(client):
    # 1. Brute-force login must be throttled to 429 within the window
    fake_email = f"tscheck-bruteforce-{uuid.uuid4().hex[:10]}@example.com"
    statuses = []
    for _ in range(6):
        r = client.post("/auth/login", json={"email": fake_email, "password": "wrong-password"})
        statuses.append(r.status_code)
    assert 429 in statuses, statuses
    assert statuses[-1] == 429, statuses

    # 2. CORS must not reflect an untrusted origin
    with httpx.Client(base_url=API_URL, timeout=30.0) as anon:
        r = anon.get("/auctions", headers={"Origin": "https://evil-attacker.example.com"})
        allow_origin = r.headers.get("access-control-allow-origin", "")
        assert allow_origin != "https://evil-attacker.example.com", r.headers

    # 3. Login cookie must be Secure + HttpOnly + SameSite=Lax
    login = client.post("/auth/login", json={"email": "pbrkejarijember@gmail.com", "password": "@Papbbjember1234"})
    assert login.status_code == 200, (login.status_code, login.text[:300])
    set_cookie = login.headers.get("set-cookie", "").lower()
    assert "secure" in set_cookie and "httponly" in set_cookie and "samesite=lax" in set_cookie, set_cookie

    # 4. Security headers present on a normal response
    root = client.get("/")
    assert root.headers.get("x-content-type-options") == "nosniff"
    assert root.headers.get("x-frame-options") == "DENY"
    assert "default-src" in root.headers.get("content-security-policy", "")
    client.post("/auth/logout")
