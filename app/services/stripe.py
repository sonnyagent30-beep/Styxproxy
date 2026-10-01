"""Stripe payment gateway.

Thin provider module mirroring flutterwave.py. Creates Stripe Checkout
sessions (hosted by Stripe) and verifies webhooks (HMAC-SHA256 of the raw
body with the webhook secret, sent in the Stripe-Signature header).
"""

import hashlib
import hmac
import logging
import uuid
from typing import Any

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

STRIPE_BASE = "https://api.stripe.com/v1"


def verify_stripe_signature(payload_bytes: bytes, signature: str) -> bool:
    """Verify Stripe webhook signature (HMAC-SHA256 of raw body with webhook secret)."""
    if not settings.stripe_webhook_secret or not signature:
        return False
    # Stripe sends "t=<timestamp>,v1=<hmac_sha256>" — extract v1
    parts = {p.split("=", 1)[0]: p.split("=", 1)[1] for p in signature.split(",") if "=" in p}
    v1 = parts.get("v1", "")
    computed = hmac.new(
        settings.stripe_webhook_secret.encode(), payload_bytes, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(computed, v1)


async def create_stripe_checkout_session(
    amount_ngn: float,
    customer_email: str,
    customer_phone: str,
    callback_url: str,
    description: str | None = None,
    device_id: str | None = None,
) -> dict[str, Any]:
    """Create a Stripe Checkout session. Returns {payment_id, checkout_url, tx_ref}.

    Stripe doesn't natively support NGN. We convert to USD via a simple estimate
    (Stripe accepts any currency in its zero-decimal format, but for NGN we need
    to handle kobo conversion). We use USD as the checkout currency and convert
    the NGN amount to USD using Stripe's exchange rate.

    Note: In production, use Stripe's `automatic_currency` feature or
    convert NGN→USD before calling this. For now, we send the amount in cents
    (USD) with a note.
    """
    if not settings.stripe_secret_key:
        raise ValueError("Stripe gateway is not configured")

    tx_ref = f"TXS-{uuid.uuid4().hex[:8].upper()}"

    # NGN → USD estimate (simplified; use a real forex API in production)
    # Stripe's zero-decimal currency: NGN is zero-decimal for Stripe's purposes
    # but we'll use USD for the checkout and convert
    # Fallback: assume 1 USD = 1500 NGN (rough estimate — real implementation
    # should fetch from a forex API like exchangerate.host)
    usd_amount_cents = int((amount_ngn / 1500) * 100)

    async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=5.0)) as client:
        response = await client.post(
            f"{STRIPE_BASE}/checkout/sessions",
            headers={
                "Authorization": f"Bearer {settings.stripe_secret_key}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={
                "mode": "payment",
                "success_url": f"{callback_url}?tx_ref={tx_ref}&session_id={{CHECKOUT_SESSION_ID}}",
                "cancel_url": callback_url,
                "customer_email": customer_email,
                "line_items[0][price_data][currency]": "usd",
                "line_items[0][price_data][product_data][name]": description or "Styxproxy Proxy Service",
                "line_items[0][price_data][unit_amount]": str(usd_amount_cents),
                "line_items[0][quantity]": "1",
                "metadata[tx_ref]": tx_ref,
                **( {"metadata[device_id]": device_id} if device_id else {} ),
            },
        )
        response.raise_for_status()
        data = response.json()
        return {
            "payment_id": data.get("id", tx_ref),
            "checkout_url": data.get("url", ""),
            "tx_ref": tx_ref,
        }
