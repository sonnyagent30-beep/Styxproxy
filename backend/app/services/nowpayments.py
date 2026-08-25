"""NOWPayments crypto gateway (USDT, BTC, etc.).

Thin provider module mirroring flutterwave.py. Creates hosted crypto
invoices and verifies IPN callbacks (HMAC-SHA512 of the raw JSON body,
sorted-keys canonical form, with the IPN secret in x-nowpayments-sig).
"""

import hashlib
import hmac
import json
import logging
import uuid
from typing import Any, Optional

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def verify_nowpayments_signature(payload_bytes: bytes, signature: str) -> bool:
    """NOWPayments signs IPNs as HMAC-SHA512 over the sorted-keys JSON dump."""
    if not settings.nowpayments_ipn_secret or not signature:
        return False
    try:
        parsed = json.loads(payload_bytes)
        canonical = json.dumps(parsed, sort_keys=True, separators=(",", ":"))
    except (json.JSONDecodeError, TypeError):
        return False
    computed = hmac.new(settings.nowpayments_ipn_secret.encode(), canonical.encode(), hashlib.sha512).hexdigest()
    return hmac.compare_digest(computed, signature)


async def create_nowpayments_invoice(
    amount_ngn: float,
    customer_email: str,
    customer_phone: str,
    callback_url: str,
    description: Optional[str] = None,
    device_id: str | None = None,
) -> dict[str, Any]:
    """Create a NOWPayments invoice. Returns {payment_id, checkout_url, tx_ref}.

    NOWPayments does not natively price in NGN — we convert to USD via their
    fiat estimate endpoint at creation time.
    """
    if not settings.nowpayments_api_key:
        raise ValueError("Crypto gateway is not configured")

    base = settings.nowpayments_base_url.rstrip("/")
    tx_ref = f"TXC-{uuid.uuid4().hex[:8].upper()}"

    async with httpx.AsyncClient(timeout=httpx.Timeout(15.0, connect=5.0)) as client:
        # NGN → USD conversion via NOWPayments estimate
        est = await client.get(
            f"{base}/v1/price",
            params={"currency_from": "ngn", "currency_to": "usd", "fiat_equivalent": "usd"},
        )
        usd_amount = None
        try:
            rate = float(est.json().get("estimated_amount", 0) or 0)  # USD per 1 NGN
            if rate > 0:
                usd_amount = round(amount_ngn * rate, 2)
        except Exception:
            logger.warning("NOWPayments price estimate failed; falling back to fixed rate lookup")
        if not usd_amount or usd_amount <= 0:
            raise ValueError("Could not determine crypto price for amount")

        body: dict[str, Any] = {
            "price_amount": usd_amount,
            "price_currency": "usd",
            "pay_currency": "usdttrc20",  # default; payer can switch on invoice page
            "order_id": tx_ref,
            "order_description": description or "Proxy service payment",
            "success_url": callback_url,
            "cancel_url": callback_url,
        }
        if customer_email:
            body["customer_email"] = customer_email

        response = await client.post(
            f"{base}/v1/invoice",
            headers={"x-api-key": settings.nowpayments_api_key},
            json=body,
        )
        response.raise_for_status()
        data = response.json()
        return {
            "payment_id": str(data.get("id", "")),
            "checkout_url": data.get("invoice_url", ""),
            "tx_ref": tx_ref,
        }
