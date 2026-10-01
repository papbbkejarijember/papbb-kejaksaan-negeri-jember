from conftest import login_as

ADMIN_EMAIL = "pbrkejarijember@gmail.com"
ADMIN_PASSWORD = "@Papbbjember1234"


def test_official_admin_logs_in_and_old_demo_admin_is_rejected(client):
    # Official admin succeeds
    r = login_as(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    assert r.status_code == 200, (r.status_code, r.text[:300])
    me = client.get("/auth/me")
    assert me.status_code == 200 and me.json()["role"] == "admin"
    dashboard = client.get("/auctions/dashboard/admin")
    assert dashboard.status_code == 200, (dashboard.status_code, dashboard.text[:300])
    client.post("/auth/logout")

    # Old demo admin credentials from the previous build must now be rejected
    r2 = client.post("/auth/login", json={"email": "admin@kejari-jember.go.id", "password": "AdminJember123!"})
    assert r2.status_code == 401, (r2.status_code, r2.text[:300])
