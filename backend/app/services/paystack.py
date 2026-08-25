"""Paystack payment gateway.

Thin provider module mirroring flutterwave.py. Creates hosted checkout
transactions and verifies webhooks (HMAC-SHA512 of the raw body with the
secret key, sent in the X-Paystack-Signature header).
"""

import hashlib
import hmac
import logging
from typing import Any

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

PAYSTACK_BASE = "https://api.paystack.co"


def verify_paystack_signature(payload_bytes: bytes, signature: str) -> bool:
    """Paystack signs webhooks with HMAC-SHA512(secret_key, raw_body)."""
    if not settings.paystack_secret_key or not signature:
        return False
    computed = hmac.new(settings.paystack_secret_key.encode(), payload_bytes, hashlib.sha512).hexdigest()
    return hmac.compare_digest(computed, signature)


async def create_paystack_transaction(
    amount_ngn: float,
    customer_email: str,
    customer_phone: str,
    callback_url: str,
    description: str | None = None,
    device_id: str | None = None,
) -> dict[str, Any]:
    """Initialize a Paystack transaction. Returns {payment_id, checkout_url, tx_ref}."""
    if not settings.paystack_secret_key:
        raise ValueError("Paystack gateway is not configured")

    tx_ref = f"TXP-{__import__('uuid').uuid4().hex[:8].upper()}"
    async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=5.0)) as client:
        response = await client.post(
            f"{PAYSTACK_BASE}/transaction/initialize",
            headers={
                "Authorization": f"Bearer {settings.paystack_secret_key}",
                "Content-Type": "application/json",
            },
            json={
                "email": customer_email,
                "amount": int(amount_ngn * 100),  # kobo
                "currency": "NGN",
                "reference": tx_ref,
                "callback_url": callback_url,
                "metadata": (
                    {"device_id": device_id, "description": description}
                    if description
                    else {"device_id": device_id}
                    if device_id
                    else None
                ),
            },
        )
        response.raise_for_status()
        data = response.json()
        if data.get("status") is not True:
            raise ValueError(f"Paystack init failed: {data.get('message', 'unknown')}")
        d = data.get("data", {})
        return {
            "payment_id": str(d.get("access_code") or tx_ref),
            "checkout_url": d.get("authorization_url", ""),
            "tx_ref": tx_ref,
        }
