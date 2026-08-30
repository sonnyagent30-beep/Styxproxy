"""Paynow crypto payment gateway.

Thin provider module mirroring nowpayments.py. Paynow provides crypto payment
invoices with hosted checkout pages. Supports BTC, USDT, ETH, and other
major cryptocurrencies.
"""

import hashlib
import hmac
import json
import logging
import uuid
from typing import Any

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def verify_paynow_signature(payload_bytes: bytes, signature: str) -> bool:
    """Verify Paynow webhook signature (HMAC-SHA512 of raw body with API secret)."""
    if not settings.paynow_api_secret or not signature:
        return False
    computed = hmac.new(
        settings.paynow_api_secret.encode(), payload_bytes, hashlib.sha512
    ).hexdigest()
    return hmac.compare_digest(computed, signature)


async def create_paynow_invoice(
    amount_ngn: float,
    customer_email: str,
    customer_phone: str,
    callback_url: str,
    description: str | None = None,
    device_id: str | None = None,
) -> dict[str, Any]:
    """Create a Paynow crypto invoice. Returns {payment_id, checkout_url, tx_ref}.

    Paynow is a crypto-focused payment gateway. It accepts NGN and auto-converts
    to cryptocurrency at checkout. We send NGN as the fiat currency and let
    Paynow handle the conversion.
    """
    if not settings.paynow_api_key:
        raise ValueError("Paynow gateway is not configured")

    base = settings.paynow_base_url.rstrip("/")
    tx_ref = f"TXPN-{uuid.uuid4().hex[:8].upper()}"

    async with httpx.AsyncClient(timeout=httpx.Timeout(15.0, connect=5.0)) as client:
        response = await client.post(
            f"{base}/v1/invoices",
            headers={
                "Authorization": f"Bearer {settings.paynow_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "amount": amount_ngn,
                "currency": "NGN",
                "customer_email": customer_email,
                "customer_phone": customer_phone,
                "description": description or "Styxproxy Proxy Service",
                "callback_url": callback_url,
                "redirect_url": callback_url,
                "reference": tx_ref,
                **( {"metadata": {"device_id": device_id}} if device_id else {} ),
            },
        )
        response.raise_for_status()
        data = response.json()
        # Paynow API response structure: { invoice_id, payment_url, reference }
        d = data.get("data", data)
        return {
            "payment_id": d.get("invoice_id", d.get("id", tx_ref)),
            "checkout_url": d.get("payment_url", d.get("checkout_url", "")),
            "tx_ref": tx_ref,
        }
