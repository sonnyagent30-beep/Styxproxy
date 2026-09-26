"""Admin webhook service for real-time event notifications."""

import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AdminWebhook, AdminWebhookLog

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_DELAYS = [1, 2, 4]  # seconds


def _hash_secret(secret: str) -> str:
    """Hash webhook secret for storage."""
    return hashlib.sha256(secret.encode()).hexdigest()


def _generate_signature(payload: str, secret: str) -> str:
    """Generate HMAC-SHA256 signature for webhook payload."""
    return hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()


async def send_webhook(
    session: AsyncSession,
    webhook: AdminWebhook,
    event: str,
    payload: dict[str, Any],
) -> bool:
    """Send webhook delivery with retry logic. Returns True if delivered."""
    payload_str = json.dumps(payload, default=str)
    # We need the secret to sign — but we only store the hash.
    # In production, store encrypted secret. For now, use a placeholder.
    # TODO: Implement encrypted secret storage
    signature = _generate_signature(payload_str, "placeholder-secret")

    headers = {
        "Content-Type": "application/json",
        "X-Webhook-Event": event,
        "X-Webhook-Signature": signature,
        "X-Webhook-Delivery": str(datetime.now(timezone.utc).isoformat()),
    }

    delivered = False
    last_status = None
    last_body = ""

    for attempt in range(MAX_RETRIES):
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(webhook.url, json=payload, headers=headers)
                last_status = response.status_code
                last_body = response.text[:500]

                if response.status_code < 500:
                    delivered = response.status_code < 400
                    break

        except Exception as e:
            logger.warning(f"Webhook delivery attempt {attempt + 1} failed: {e}")
            last_body = str(e)

        if attempt < MAX_RETRIES - 1:
            import asyncio
            await asyncio.sleep(RETRY_DELAYS[attempt])

    # Log delivery attempt
    log_entry = AdminWebhookLog(
        webhook_id=webhook.id,
        event=event,
        payload=payload,
        response_status=last_status,
        response_body=last_body,
        delivered=delivered,
        retry_count=attempt + 1,
    )
    session.add(log_entry)
    await session.commit()

    return delivered


async def trigger_event(
    session: AsyncSession,
    event: str,
    payload: dict[str, Any],
) -> int:
    """Trigger all active webhooks subscribed to an event. Returns delivery count."""
    stmt = select(AdminWebhook).where(
        AdminWebhook.is_active == True,
        AdminWebhook.events.contains([event]),
    )
    result = await session.execute(stmt)
    webhooks = result.scalars().all()

    delivered_count = 0
    for webhook in webhooks:
        try:
            if await send_webhook(session, webhook, event, payload):
                delivered_count += 1
        except Exception as e:
            logger.error(f"Failed to send webhook {webhook.id}: {e}")

    return delivered_count
