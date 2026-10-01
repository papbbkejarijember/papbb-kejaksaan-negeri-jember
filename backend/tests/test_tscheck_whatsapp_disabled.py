import uuid

from conftest import pin_session_cookie


def test_whatsapp_channel_rejected_while_email_channel_stays_active(client):
    email = f"tscheck-wa-{uuid.uuid4().hex[:10]}@example.com"
    r = client.post(
        "/auth/register",
        json={"full_name": "Tscheck WhatsApp", "email": email, "password": "Strong@Test123", "legal_consent": True},
    )
    assert r.status_code == 200, (r.status_code, r.text[:300])
    pin_session_cookie(client, r)

    config = client.get("/notifications/config")
    assert config.status_code == 200, (config.status_code, config.text[:300])
    assert config.json()["whatsapp_mode"] == "disabled", config.json()

    wa = client.post(
        "/notifications/test",
        json={"channels": ["whatsapp"], "subject": "tscheck whatsapp probe", "message": "should be rejected"},
    )
    assert wa.status_code == 409, (wa.status_code, wa.text[:300])

    mail = client.post(
        "/notifications/test",
        json={"channels": ["email"], "subject": "tscheck email probe", "message": "email channel should stay active"},
    )
    assert mail.status_code == 200, (mail.status_code, mail.text[:300])
    body = mail.json()
    assert any(n["channel"] == "email" for n in body["notifications"]), body
