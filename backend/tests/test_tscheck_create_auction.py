from datetime import datetime, timedelta, timezone

def test_admin_creates_active_auction(client):
    client.post('/auth/login', json={'email':'admin@kejari-jember.go.id','password':'AdminJember123!'}).raise_for_status()
    now = datetime.now(timezone.utc)
    payload={'title':'tscheck-create-active','category':'Kendaraan','description':'Objek uji lelang aktif untuk verifikasi portal.','location':'Jember','limit_price':12345000,'increment':250000,'starts_at':(now-timedelta(minutes=5)).isoformat(),'ends_at':(now+timedelta(days=1)).isoformat()}
    r=client.post('/auctions',json=payload)
    assert r.status_code==200,(r.status_code,r.text[:300])
    created=r.json(); assert created['title']==payload['title'] and created['status']=='ongoing'
    listed=client.get('/auctions',params={'search':payload['title']})
    assert listed.status_code==200 and any(x['id']==created['id'] for x in listed.json())
