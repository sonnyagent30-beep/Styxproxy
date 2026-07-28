"""n8n webhook service for triggering automation workflows."""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)


async def trigger_credentials_delivered_webhook(
    order_id: str,
    tx_ref: str,
    phone: str,
    channel: str,
    bun_username: str,
    bun_password: str,
    proxy_ip: str,
    proxy_port: int,
    expires_at: datetime,
    receipt_url: Optional[str] = None,
) -> bool:
    """
    Fire-and-forget webhook to n8n with credential delivery info.

    Sends a POST to n8n.styxproxy.com/webhook/credentials-delivered with:
    {
        "order_id": "ORD-XXXXXX",
        "tx_ref": "TXF-XXXXXX",
        "phone": "+234...",
        "channel": "whatsapp",
        "bun_username": "bun_xxxxxx",
        "bun_password": "xxxxxx",
        "proxy_ip": "192.168.x.x",
        "proxy_port": 1080,
        "expires_at": "2026-08-15T12:00:00Z",
        "receipt_url": "https://..."
    }

    Returns True if webhook was sent (fire-and-forget, errors are logged but not raised).
    Failures are recorded to Redis (key n8n:failures, capped at 100) so admin
    can view them via GET /admin/api/n8n/failures. Bug walk theme-B fix.
    """
    settings = get_settings()
    webhook_url = settings.n8n_webhook_url

    if not webhook_url:
        logger.warning("n8n webhook URL not configured, skipping credential delivery notification")
        return False

    payload = {
        "order_id": order_id,
        "tx_ref": tx_ref,
        "phone": phone,
        "channel": channel,
        "bun_username": bun_username,
        "bun_password": bun_password,
        "proxy_ip": proxy_ip,
        "proxy_port": proxy_port,
        "expires_at": expires_at.isoformat() if isinstance(expires_at, datetime) else expires_at,
    }

    if receipt_url:
        payload["receipt_url"] = receipt_url

    async def _send_webhook() -> bool:
        """Background task to send webhook (logs errors but doesn't raise)."""
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=5.0)) as client:
                response = await client.post(webhook_url, json=payload)
                response.raise_for_status()
                logger.info(f"n8n credentials-delivered webhook sent for order {order_id}")
                return True
        except httpx.HTTPError as e:
            logger.error(f"n8n webhook failed for order {order_id}: {e}")
            await _record_failure(order_id, tx_ref, str(e), payload)
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending n8n webhook for order {order_id}: {e}")
            await _record_failure(order_id, tx_ref, f"unexpected: {e}", payload)
            return False

    # Fire and forget - don't await, just schedule and return immediately
    asyncio.create_task(_send_webhook())
    return True


async def _record_failure(
    order_id: str,
    tx_ref: str,
    error: str,
    payload: dict[str, Any],
) -> None:
    """Record a webhook failure in Redis so admin can review.

    Stored in a Redis list capped at 100 entries (LPUSH + LTRIM).
    Includes order_id, tx_ref, timestamp, error message. Sensitive
    fields (bun_password) are stripped before storage.
    """
    try:
        from app.services.observability import get_redis

        client = await get_redis()
        if client is None:
            return

        # Strip secrets before logging
        safe_payload = {k: v for k, v in payload.items() if k != "bun_password"}

        entry = json.dumps(
            {
                "order_id": order_id,
                "tx_ref": tx_ref,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": error[:500],  # cap error length
                "payload_summary": {
                    "channel": safe_payload.get("channel"),
                    "proxy_ip": safe_payload.get("proxy_ip"),
                    "proxy_port": safe_payload.get("proxy_port"),
                },
            }
        )

        # LPUSH + LTRIM to keep most recent 100 failures
        await client.lpush("n8n:failures", entry)
        await client.ltrim("n8n:failures", 0, 99)

        # Increment counter for daily monitoring (48h TTL = covers day + buffer)
        await client.incr("n8n:failures:today")
        await client.expire("n8n:failures:today", 172800)

        # Spike detection: if 5+ failures in the buffer window, log Sentry-worthy warning
        total_failures = await client.llen("n8n:failures")
        if total_failures >= 5:
            logger.warning(
                f"n8n webhook failure spike: {total_failures} failures in buffer. "
                f"Most recent: order={order_id} tx_ref={tx_ref} error={error[:200]}"
            )
    except Exception as exc:
        # Never let the failure-recording itself raise
        logger.error(f"Failed to record n8n webhook failure to Redis: {exc}")


async def get_failures(limit: int = 50) -> list[dict[str, Any]]:
    """Read recent webhook failures (admin endpoint helper).

    Returns the most recent `limit` failures as parsed dicts. Newest first.
    Returns [] if Redis is unavailable or key is empty.
    """
    try:
        from app.services.observability import get_redis

        client = await get_redis()
        if client is None:
            return []

        raw_list = await client.lrange("n8n:failures", 0, limit - 1)
        results = []
        for raw in raw_list:
            try:
                results.append(json.loads(raw))
            except json.JSONDecodeError:
                continue
        return results
    except Exception as exc:
        logger.error(f"Failed to read n8n webhook failures from Redis: {exc}")
        return []


async def get_failure_stats() -> dict[str, Any]:
    """Read failure stats: buffer size + 48h counter."""
    try:
        from app.services.observability import get_redis

        client = await get_redis()
        if client is None:
            return {"buffer_size": 0, "last_48h_count": 0}

        buffer_size = await client.llen("n8n:failures")
        counter_raw = await client.get("n8n:failures:today")
        counter = int(counter_raw) if counter_raw else 0
        return {"buffer_size": buffer_size, "last_48h_count": counter}
    except Exception as exc:
        logger.error(f"Failed to read n8n failure stats: {exc}")
        return {"buffer_size": 0, "last_48h_count": 0}


async def clear_failures() -> int:
    """Clear the failures buffer. Returns number of entries cleared."""
    try:
        from app.services.observability import get_redis

        client = await get_redis()
        if client is None:
            return 0

        size = await client.llen("n8n:failures")
        await client.delete("n8n:failures")
        await client.delete("n8n:failures:today")
        return size
    except Exception as exc:
        logger.error(f"Failed to clear n8n failures: {exc}")
        return 0