import os
import time
import uuid

import pymongo
import yaml

from conftest import login_as

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "app")
CRON_SECRET = os.environ.get("WEBHOOK_CRON_SECRET", "")
CRON_YAML_PATH = "/app/.emergent/crons.yml"


def test_weekly_backup_cron_ready_but_disabled(client):
    # Cron definition must be valid, scheduled weekly, and disabled without S3 credentials
    with open(CRON_YAML_PATH) as handle:
        config = yaml.safe_load(handle)
    jobs = config["crons"]
    backup_job = next(j for j in jobs if "backup" in j["name"])
    assert backup_job["enabled"] is False, backup_job
    assert backup_job["cron"], backup_job
    assert backup_job["method"] == "POST"
    assert "weekly-backup" in backup_job["endpoint"]

    # Backend must reject an unauthenticated/incorrectly authenticated cron call
    unauth = client.post("/cron/weekly-backup", json={"event": "schedule.triggered"})
    assert unauth.status_code == 401, (unauth.status_code, unauth.text[:300])

    assert CRON_SECRET, "WEBHOOK_CRON_SECRET must be configured for the bearer-authenticated cron endpoint"
    run_id = f"tscheck-backup-{uuid.uuid4().hex[:10]}"
    r = client.post(
        "/cron/weekly-backup",
        json={"event": "schedule.triggered", "run_id": run_id},
        headers={"Authorization": f"Bearer {CRON_SECRET}"},
    )
    assert r.status_code == 202, (r.status_code, r.text[:300])
    assert r.json()["accepted"] is True and r.json()["duplicate"] is False

    # Idempotent: same run_id repeated is acknowledged as duplicate
    r2 = client.post(
        "/cron/weekly-backup",
        json={"event": "schedule.triggered", "run_id": run_id},
        headers={"Authorization": f"Bearer {CRON_SECRET}"},
    )
    assert r2.status_code == 202
    assert r2.json()["duplicate"] is True

    # Manual run must be recorded as "skipped" because S3 credentials are not configured
    mongo = pymongo.MongoClient(MONGO_URL)
    try:
        record = None
        for _ in range(20):
            record = mongo[DB_NAME].backup_runs.find_one({"run_id": run_id})
            if record and record.get("completed_at"):
                break
            time.sleep(0.5)
        assert record is not None, "backup run was never recorded"
        assert record["status"] == "skipped", record
        assert record.get("error") == "S3 credentials not configured"
    finally:
        mongo.close()

    assert os.environ.get("BACKUP_ENABLED", "false").lower() != "true"
    assert os.environ.get("BACKUP_RETENTION_DAYS", "90") == "90" or int(os.environ.get("BACKUP_RETENTION_DAYS", "90")) == 90
