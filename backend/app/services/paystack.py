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


class PaystackRefundError(RuntimeError):
    """Paystack was asked to refund and did not confirm the money movement.

    Raised instead of returning a partial result so that no caller can flip an
    order to `refunded` on a response that does not actually mean "money back".
    """


async def refund_paystack_transaction(
    reference: str,
    amount_ngn: float,
    reason: str | None = None,
    secret_key: str | None = None,
) -> dict[str, Any]:
    """Refund a Paystack transaction. Returns the gateway's refund payload.

    Paystack refunds against a numeric TRANSACTION ID, so the reference we hold
    (TXP-/TXF-) is first resolved via `GET /transaction/verify/{reference}`.
    That verify call is also the only way to learn the amount Paystack actually
    charged and whether it was already refunded — both of which we must not
    guess at.

    Amount is sent in KOBO, the same subunit convention as
    `create_paystack_transaction` (Flutterwave is the opposite — major units).

    Raises `PaystackRefundError` on any non-confirmation: unconfigured gateway,
    unknown reference, transaction not successful, already refunded, or an HTTP
    error. On success the returned dict carries at least `id` and `status`.
    """
    secret = secret_key if secret_key is not None else settings.paystack_secret_key
    if not secret:
        raise PaystackRefundError("Paystack gateway is not configured (no secret key)")
    if not reference:
        raise PaystackRefundError("no Paystack reference to refund")
    amount_ngn = float(amount_ngn or 0)
    if amount_ngn <= 0:
        raise PaystackRefundError(f"refund amount must be > 0 (got {amount_ngn})")

    headers = {"Authorization": f"Bearer {secret}", "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=5.0)) as client:
        try:
            verify_resp = await client.get(f"{PAYSTACK_BASE}/transaction/verify/{reference}", headers=headers)
        except httpx.HTTPError as e:
            raise PaystackRefundError(f"Paystack verify failed for {reference}: {e}") from e
        if verify_resp.status_code != 200:
            raise PaystackRefundError(
                f"Paystack verify returned {verify_resp.status_code} for {reference}: {verify_resp.text[:300]}"
            )
        try:
            tx = (verify_resp.json().get("data") or {})
        except ValueError as e:
            raise PaystackRefundError(f"Paystack verify returned non-JSON for {reference}") from e

        if tx.get("status") != "success":
            raise PaystackRefundError(
                f"Paystack transaction {tx.get('id', reference)} is '{tx.get('status')}', not 'success' — refusing to refund"
            )
        if tx.get("refunded"):
            raise PaystackRefundError(f"Paystack transaction {tx.get('id', reference)} is already fully refunded")

        tx_id = tx.get("id")
        if not tx_id:
            raise PaystackRefundError(f"Paystack verify returned no transaction id for {reference}")

        charged_ngn = float(tx.get("amount") or 0) / 100.0
        if charged_ngn <= 0:
            raise PaystackRefundError(
                f"Paystack reports no captured amount for {reference} — capture cannot be proven, refusing to refund"
            )
        if amount_ngn > charged_ngn:
            # Refunding more than was captured would be declined by Paystack, but
            # fail loudly here rather than after a round trip.
            raise PaystackRefundError(
                f"refund amount {amount_ngn} exceeds captured amount {charged_ngn} for {reference}"
            )

        payload: dict[str, Any] = {"amount": int(round(amount_ngn * 100)), "currency": "NGN"}
        if reason:
            payload["merchant_note"] = reason[:200]
        try:
            refund_resp = await client.post(f"{PAYSTACK_BASE}/transaction/{tx_id}/refund", headers=headers, json=payload)
        except httpx.HTTPError as e:
            raise PaystackRefundError(f"Paystack refund call failed for {tx_id}: {e}") from e

        if refund_resp.status_code != 200:
            raise PaystackRefundError(
                f"Paystack refund returned {refund_resp.status_code} for {tx_id}: {refund_resp.text[:300]}"
            )
        try:
            body = refund_resp.json()
        except ValueError as e:
            raise PaystackRefundError(f"Paystack refund returned non-JSON for {tx_id}") from e

        if body.get("status") is not True:
            raise PaystackRefundError(f"Paystack refund rejected for {tx_id}: {body.get('message', 'unknown')}")

        data = body.get("data") or {}
        if not data.get("id"):
            raise PaystackRefundError(f"Paystack refund response carried no refund id for {tx_id}")
        return data


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

    Returns {payment_id, checkout_url, tx_ref, provider_order_id}.

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
        return {
            "payment_id": str(d.get("access_code") or tx_ref),
            "checkout_url": d.get("authorization_url", ""),
            "tx_ref": gateway_reference,
            "provider_order_id": str(gateway_id) if gateway_id is not None else None,
        }
