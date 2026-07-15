"""n8n webhook service for triggering automation workflows."""
import asyncio
import logging
from datetime import datetime
from typing import Optional

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
    
    Sends a POST to n8n.bunche.ng/webhook/credentials-delivered with:
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
    
    async def _send_webhook():
        """Background task to send webhook (logs errors but doesn't raise)."""
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=5.0)) as client:
                response = await client.post(webhook_url, json=payload)
                response.raise_for_status()
                logger.info(f"n8n credentials-delivered webhook sent for order {order_id}")
                return True
        except httpx.HTTPError as e:
            logger.error(f"n8n webhook failed for order {order_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending n8n webhook for order {order_id}: {e}")
            return False
    
    # Fire and forget - don't await, just schedule and return immediately
    asyncio.create_task(_send_webhook())
    return True
