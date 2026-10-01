"""Paystack payment gateway.

Thin provider module mirroring flutterwave.py. Creates hosted checkout
transactions and verifies webhooks (HMAC-SHA512 of the raw body with the
secret key, sent in the X-Paystack-Signature header).
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
    tx_ref: str | None = None,
) -> dict[str, Any]:
    """Initialize a Paystack transaction.

    Returns {payment_id, checkout_url, tx_ref, provider_order_id, gateway_amount,
    gateway_currency}.

    `gateway_amount` is the amount **Paystack itself echoed back**, in KOBO
    (Paystack's `amount` is the currency subunit, the opposite convention from
    Flutterwave v3). It is returned so the caller can persist what the gateway
    says it will charge instead of re-deriving it from our own invoice total —
    if those ever diverge, only the gateway's figure is worth reconciling
    against. May be None if Paystack omits it; callers must not substitute a
    locally computed value.

    `tx_ref` MUST be the backend-owned reference that the caller also writes
    to `orders.payment_reference`. This function used to mint its own
    `TXP-` reference and ignore the caller's, so the order row stored a
    `TXF-` value while Paystack charged and echoed back `TXP-` — a join that
    can never match, which silently made every Paystack order unfulfillable.
    The webhook joins on `orders.payment_reference`, so the reference we SEND
    is the reference we must STORE.

    `tx_ref=None` still mints a `TXP-` reference so no other caller breaks,
    but any caller that does that must persist the returned `tx_ref` too.
    """
    if not settings.paystack_secret_key:
        raise ValueError("Paystack gateway is not configured")

    tx_ref = tx_ref or f"TXP-{uuid.uuid4().hex[:8].upper()}"
    async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=5.0)) as client:
        response = await client.post(
            f"{PAYSTACK_BASE}/transaction/initialize",
            headers={
                "Authorization": f"Bearer {settings.paystack_secret_key}",
                "Content-Type": "application/json",
            },
            json={
                "email": customer_email,
                # Paystack's `amount` IS the currency SUBUNIT (kobo) — this is the
                # opposite convention from Flutterwave v3. N5000 must be sent as
                # 500000. Removing the *100 here would undercharge by 100x.
                "amount": int(amount_ngn * 100),  # kobo
                "currency": "NGN",
                "reference": tx_ref,
                "callback_url": callback_url + f"&tx_ref={tx_ref}",
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
        # Persist the gateway's OWN echo of the reference and its numeric
        # transaction id, not just what we sent. `reference` is what Paystack
        # will sign into the webhook, and `id` is the only key that can still
        # join a legacy order whose stored reference diverged (see
        # `provider_order_id` on Order). If Paystack ever normalises the
        # reference we sent, the response is the only trustworthy record of
        # what was actually charged.
        gateway_reference = d.get("reference") or tx_ref
        gateway_id = d.get("id")
        # The gateway's OWN amount + currency, echoed from the initialize
        # response. Persisted by the caller as pending capture evidence so the
        # charged figure is never re-derived from our invoice total. Paystack
        # reports the SUBUNIT here, hence the caller's /100.
        gateway_amount = d.get("amount")
        gateway_currency = d.get("currency")
        return {
            "payment_id": str(d.get("access_code") or tx_ref),
            "checkout_url": d.get("authorization_url", ""),
            "tx_ref": gateway_reference,
            "provider_order_id": str(gateway_id) if gateway_id is not None else None,
            "gateway_amount": gateway_amount,
            "gateway_currency": gateway_currency,
        }
