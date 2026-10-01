"""n8n webhook service for triggering automation workflows."""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)



async def deliver_credentials_direct(
    order_id: str,
    tx_ref: str,
    phone: str,
    channel: str,
    styxproxy_username: str,
    styxproxy_password: str,
    proxy_ip: str,
    proxy_port: int,
    expires_at: datetime,
    receipt_url: Optional[str] = None,
) -> bool:
    """Directly deliver credentials via Charon API (bypasses n8n webhook).

    This is the *fallback* path, so it must never raise. The contract is
    `-> bool` and the caller records that bool in the delivery ledger — a
    raised exception either aborts fulfilment or, behind a bare `except`,
    gets swallowed into a false "delivered" row. Both outcomes are the
    "told it succeeded, actually failed" defect this function exists to
    avoid, so config resolution (which can fail) lives *inside* the try
    alongside the transport call.

    The URL was previously built from `settings.api_base_url`, a field that
    was never defined on Settings. Because that line sat outside the try, it
    raised AttributeError on 100% of calls and the fallback never once
    delivered anything (t_4007d162).
    """
    try:
        settings = get_settings()
        charon_url = f"{settings.api_base_url}/api/v1/charon/reply"
    except Exception as e:
        # Config/import failure. Log loudly — this means the fallback is dead
        # in this deployment — and report failure rather than propagating.
        logger.error(
            f"Charon direct delivery cannot start for order {order_id}: {e}. "
            "Check that API_BASE_URL is set and app.config imports cleanly."
        )
        return False

    message = f"""Your proxy credentials are ready!

Proxy: {proxy_ip}:{proxy_port}
Username: {styxproxy_username}
Password: {styxproxy_password}
Expires: {expires_at}

Receipt: {receipt_url or 'N/A'}"""

    # ChatReplyRequest (app/routers/charon.py) declares `user_message` as a
    # required str and `customer_phone` for the contact. This payload used to
    # send `message` and `phone`, which are NOT fields on the model — every
    # call returned 422 "user_message: Field required" and the direct-delivery
    # fallback silently failed. Field names are a contract; drift is silent
    # until something 422s in production.
    #
    # Every value is coerced to str: user_message is typed `str`, and JS-style
    # `+` concatenation over a None or int field (proxy_port is an int) puts a
    # non-string into it, which is the other half of "Input should be a valid
    # string".
    payload = {
        'user_message': str(message),
        'customer_phone': str(phone or ""),
        'channel': str(channel or "internal"),
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(charon_url, json=payload)
            if resp.status_code == 200:
                logger.info(f"Credentials delivered directly for order {order_id}")
                return True
            else:
                logger.warning(f"Charon direct delivery failed: {resp.status_code} {resp.text[:200]}")
                return False
    except Exception as e:
        logger.error(f"Charon direct delivery error: {e}")
        return False

async def trigger_credentials_delivered_webhook(
    order_id: str,
    tx_ref: str,
    phone: str,
    channel: str,
    styxproxy_username: str,
    styxproxy_password: str,
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
        "styxproxy_username": "styxproxy_xxxxxx",
        "styxproxy_password": "xxxxxx",
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
        "styxproxy_username": styxproxy_username,
        "styxproxy_password": styxproxy_password,
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

    # Await the send and report what actually happened.
    #
    # This used to be `asyncio.create_task(_send_webhook()); return True` —
    # fire-and-forget with an unconditional success. The caller could never
    # see a failure, so the `if not n8n_success:` direct-email fallback was
    # unreachable dead code: n8n could fail 100% of the time and the worker
    # still logged "delivered". A delivery path that reports success it did
    # not observe is worse than one that reports failure.
    #
    # Still bounded: the client has a 10s timeout with a 5s connect timeout,
    # so a hung n8n cannot hold up fulfillment indefinitely.
    return await _send_webhook()


async def _record_failure(
    order_id: str,
    tx_ref: str,
    error: str,
    payload: dict[str, Any],
) -> None:
    """Record a webhook failure in Redis so admin can review.

    Stored in a Redis list capped at 100 entries (LPUSH + LTRIM).
    Includes order_id, tx_ref, timestamp, error message. Sensitive
    fields (styxproxy_password) are stripped before storage.
    """
    try:
        from app.services.observability import get_redis

        client = await get_redis()
        if client is None:
            return

        # Strip secrets before logging
        safe_payload = {k: v for k, v in payload.items() if k != "styxproxy_password"}

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
