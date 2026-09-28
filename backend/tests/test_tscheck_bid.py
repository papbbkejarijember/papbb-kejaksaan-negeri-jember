from datetime import datetime,timedelta,timezone
import uuid

def test_participant_places_minimum_bid(client):
    admin=client.post('/auth/login',json={'email':'admin@kejari-jember.go.id','password':'AdminJember123!'}); assert admin.status_code==200
    now=datetime.now(timezone.utc)
    r=client.post('/auctions',json={'title':f'tscheck-bid-{uuid.uuid4().hex[:8]}','category':'Elektronik','description':'Objek uji untuk penawaran minimum peserta.','location':'Jember','limit_price':500000,'increment':50000,'starts_at':(now-timedelta(minutes=1)).isoformat(),'ends_at':(now+timedelta(hours=2)).isoformat()}); assert r.status_code==200,(r.status_code,r.text[:300])
    auction=r.json()
    client.post('/auth/login',json={'email':'peserta@kejari-jember.go.id','password':'PesertaJember123!'}).raise_for_status()
    r=client.post(f"/auctions/{auction['id']}/bids",json={'amount':500000})
    assert r.status_code==200,(r.status_code,r.text[:300]); assert r.json()['amount']==500000
    detail=client.get(f"/auctions/{auction['id']}"); assert detail.status_code==200 and detail.json()['bid_count']==1
