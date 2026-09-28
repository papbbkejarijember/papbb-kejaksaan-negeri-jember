def test_logout_clears_session_and_protected_access(client):
    client.post('/auth/login',json={'email':'peserta@kejari-jember.go.id','password':'PesertaJember123!'}).raise_for_status()
    assert client.get('/auth/me').status_code==200
    r=client.post('/auth/logout'); assert r.status_code==204,(r.status_code,r.text[:300])
    assert client.get('/auth/me').json() is None
    assert client.get('/auctions/dashboard/participant').status_code==401
