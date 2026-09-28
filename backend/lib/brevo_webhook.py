import logging
import os

import httpx


logger = logging.getLogger(__name__)
BREVO_WEBHOOKS_URL = "https://api.brevo.com/v3/webhooks"
BREVO_EVENTS = ["delivered", "opened", "hardBounce", "softBounce", "blocked", "invalid", "error"]


async def ensure_brevo_webhook() -> None:
    api_key = os.environ.get("BREVO_API_KEY")
    token = os.environ.get("BREVO_WEBHOOK_TOKEN")
    base_url = os.environ.get("APP_URL")
    if not api_key or not token or not base_url:
        logger.info("Brevo webhook registration skipped: configuration incomplete")
        return
    callback_url = base_url.rstrip("/") + "/api/webhooks/brevo"
    headers = {"accept": "application/json", "content-type": "application/json", "api-key": api_key}
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            listed = await client.get(BREVO_WEBHOOKS_URL, params={"type": "transactional"}, headers=headers)
            if listed.status_code == 400 and listed.json().get("code") == "document_not_found":
                hooks = []
            else:
                listed.raise_for_status()
                hooks = listed.json().get("webhooks", [])
            wanted = set(BREVO_EVENTS)
            fallback = wanted - {"error"}
            for hook in hooks:
                events = set(hook.get("events", []))
                if hook.get("url") == callback_url and hook.get("type") == "transactional" and events in (wanted, fallback) and not hook.get("batched", False):
                    logger.info("Brevo transactional webhook already registered")
                    return
            body = {
                "url": callback_url,
                "description": "Portal Lelang Kejari Jember email tracking",
                "type": "transactional",
                "channel": "email",
                "batched": False,
                "events": BREVO_EVENTS,
                "auth": {"type": "bearer", "token": token},
            }
            created = await client.post(BREVO_WEBHOOKS_URL, headers=headers, json=body)
            if created.status_code == 400:
                body["events"] = [event for event in BREVO_EVENTS if event != "error"]
                created = await client.post(BREVO_WEBHOOKS_URL, headers=headers, json=body)
            created.raise_for_status()
            logger.info("Brevo transactional webhook registered")
    except (httpx.HTTPError, ValueError) as exc:
        logger.error("Brevo webhook registration failed: %s", type(exc).__name__)