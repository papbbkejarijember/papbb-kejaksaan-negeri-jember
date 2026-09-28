def test_demo_admin_login_and_dashboard(client):
    r = client.post('/auth/login', json={'email':'admin@kejari-jember.go.id','password':'AdminJember123!'})
    assert r.status_code == 200, (r.status_code, r.text[:300])
    r = client.get('/auctions/dashboard/admin')
    assert r.status_code == 200, (r.status_code, r.text[:300])
    assert {'total_auctions','auctions'} <= r.json().keys()
