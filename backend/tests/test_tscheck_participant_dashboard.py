import uuid

def test_participant_registration_and_dashboard(client):
    email=f'tscheck-{uuid.uuid4().hex[:10]}@example.com'
    r=client.post('/auth/register',json={'full_name':'tscheck Participant','email':email,'phone':'628120000000','password':'TestPass123!'})
    assert r.status_code==200,(r.status_code,r.text[:300])
    r=client.get('/auctions/dashboard/participant')
    assert r.status_code==200,(r.status_code,r.text[:300])
    body=r.json(); assert body['user']['email']==email and {'bids','notifications'} <= body.keys()
