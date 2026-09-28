def test_demo_notifications_are_simulated(client):
    client.post('/auth/login',json={'email':'peserta@kejari-jember.go.id','password':'PesertaJember123!'}).raise_for_status()
    r=client.post('/notifications/test',json={'channels':['email','whatsapp'],'subject':'tscheck notification','message':'Demo notification test'})
    assert r.status_code==200,(r.status_code,r.text[:300]); body=r.json(); assert body['status']=='simulated'; assert {n['channel'] for n in body['notifications']}=={'email','whatsapp'}; assert all(n['provider']=='mock' for n in body['notifications'])
