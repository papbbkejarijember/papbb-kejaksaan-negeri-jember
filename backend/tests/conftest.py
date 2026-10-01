"""Pre-scaffolded pytest fixtures for the FastAPI backend.

Tests hit the live uvicorn process managed by supervisor (not an in-process ASGI app), so
the app under test is the same one the frontend and Playwright see. Do NOT re-create this
file — add app-specific fixtures below the marker at the bottom.
"""

import os

import httpx
import pytest
import pytest_asyncio

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8001")
API_URL = f"{BACKEND_URL}/api"


def api_url(path: str = "") -> str:
    """Absolute URL for an /api route: api_url("/status") -> http://localhost:8001/api/status."""
    return f"{API_URL}{path}"


@pytest.fixture(scope="session")
def backend_url() -> str:
    return BACKEND_URL


@pytest.fixture
def client():
    """Sync httpx client rooted at /api — the default for endpoint tests.

    Example:
        def test_status(client):
            assert client.get("/status").status_code == 200
    """
    with httpx.Client(base_url=API_URL, timeout=30.0) as c:
        yield c


@pytest_asyncio.fixture
async def aclient():
    """Async variant, for tests that also await motor/backend helpers directly."""
    async with httpx.AsyncClient(base_url=API_URL, timeout=30.0) as c:
        yield c


# --- app-specific fixtures below this line ---

SESSION_COOKIE_NAME = "kejari_session"


def login_as(client: httpx.Client, email: str, password: str):
    """Log in and force the Secure session cookie onto the client.

    The backend issues the session cookie with the Secure attribute (by design,
    for production hardening). Plain http.cookiejar / httpx will not re-send a
    Secure cookie over a plain-http connection (this test suite talks to
    http://localhost:8001), so we extract the token from Set-Cookie and pin it
    onto the client's headers explicitly instead of relying on the cookie jar.
    """
    response = client.post("/auth/login", json={"email": email, "password": password})
    if response.status_code != 200:
        return response
    set_cookie = response.headers.get("set-cookie", "")
    token = set_cookie.split(f"{SESSION_COOKIE_NAME}=", 1)[1].split(";", 1)[0]
    client.headers["Cookie"] = f"{SESSION_COOKIE_NAME}={token}"
    return response


def pin_session_cookie(client: httpx.Client, response: httpx.Response) -> None:
    """Pin a Secure session cookie from any auth response (register/login) onto the client."""
    set_cookie = response.headers.get("set-cookie", "")
    if f"{SESSION_COOKIE_NAME}=" in set_cookie:
        token = set_cookie.split(f"{SESSION_COOKIE_NAME}=", 1)[1].split(";", 1)[0]
        client.headers["Cookie"] = f"{SESSION_COOKIE_NAME}={token}"
