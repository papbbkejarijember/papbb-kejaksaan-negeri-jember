from datetime import datetime, timedelta, timezone
import uuid

from conftest import login_as

ADMIN_EMAIL = "pbrkejarijember@gmail.com"
ADMIN_PASSWORD = "@Papbbjember1234"


def test_admin_activities_are_recorded_in_audit_log(client):
    login = login_as(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    assert login.status_code == 200, (login.status_code, login.text[:300])

    now = datetime.now(timezone.utc)
    title = f"tscheck-audit-{uuid.uuid4().hex[:8]}"
    created = client.post(
        "/auctions",
        json={
            "title": title, "category": "Elektronik", "description": "Objek uji audit log lelang.",
            "location": "Jember", "limit_price": 1000000, "increment": 100000,
            "starts_at": (now - timedelta(minutes=1)).isoformat(), "ends_at": (now + timedelta(hours=2)).isoformat(),
        },
    )
    assert created.status_code == 200, (created.status_code, created.text[:300])
    auction_id = created.json()["id"]

    logs = client.get("/auth/audit-logs")
    assert logs.status_code == 200, (logs.status_code, logs.text[:300])
    entries = logs.json()

    assert any(e["action"] == "login_success" for e in entries), "no login_success audit entry found"
    assert any(e["target_id"] == auction_id for e in entries), "auction creation not audited"
