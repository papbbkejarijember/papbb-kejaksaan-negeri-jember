from datetime import datetime, timedelta, timezone

def test_public_catalog_empty_filters(client):
    r = client.get('/auctions?search=tscheck-no-such-item&category=all&status=all')
    assert r.status_code == 200, (r.status_code, r.text[:300])
    assert r.json() == []
