"""Gateway refund dispatch — the only sanctioned way to move money back.

This module exists because the refund path used to be a pure status flip:
`admin.py::_process_refund()` set `order.status = "refunded"`, revoked the
credential and emailed the customer without ever asking a gateway. All 46
`refunded` rows in production are administrative flips, not refunds — every one
has `payment_reference` set and `tx_ref` NULL, so there was never a transaction
to reconcile against.

The rule this module enforces:

    A refund is real only if the gateway says so.

`refund_at_gateway()` therefore returns a `GatewayRefund` carrying the gateway's
own refund id, and raises `GatewayRefundError` for anything short of a
confirmed money movement — unconfigured gateway, unknown reference, an order
with no capture evidence, a rejected call, or a response carrying no refund id.
Callers MUST NOT flip an order to `refunded` on anything else.

Amount: taken from the order's CAPTURE record, never from `amount_paid_ngn`
(that is the invoice amount and is populated on cancelled/expired rows too, so
it is not evidence money ever arrived). See t_c0b38088 for the capture column.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Optional

from app.config import get_settings

logger = logging.getLogger(__name__)


class GatewayRefundError(RuntimeError):
    """The gateway was asked to refund and did not confirm the money movement.

    Deliberately distinct from an empty result: a caller cannot accidentally
    treat this as success. The order must stay actionable and the admin must
    see the error.
    """


@dataclass(frozen=True)
class GatewayRefund:
    """A confirmed refund. `gateway_refund_id` is the reconciliation handle."""

    provider: str
    gateway_refund_id: str
    gateway_status: str
    reference: str
    amount_ngn: float


# Providers we can actually refund through. Anything else is a hard error —
# guessing a gateway is how money gets refunded against the wrong transaction.
SUPPORTED_PROVIDERS = ("paystack", "flutterwave")

# Column names that may carry the gateway-charged amount, in priority order.
# Item 2 (t_c0b38088) adds the capture record; until it lands we fall back to
# amount_paid_ngn and SAY SO in the log, rather than pretending it is capture.
_CAPTURE_AMOUNT_ATTRS = ("captured_amount_ngn", "gateway_amount_ngn", "charged_amount_ngn")
_CAPTURE_MARKER_ATTRS = ("captured_at", "gateway_status")


def _resolve_captured_amount(order: Any) -> tuple[Optional[float], str]:
    """Return (captured_amount_ngn, source) for an order.

    `amount_paid_ngn` is the INVOICE amount, not capture evidence — it is set on
    cancelled and expired rows too. Prefer the capture record; fall back to the
    invoice amount only when no capture column exists yet, and report which was
    used so the caller can refuse when it matters.
    """
    for attr in _CAPTURE_AMOUNT_ATTRS:
        value = getattr(order, attr, None)
        if value is not None:
            return float(value), attr

    has_marker = any(getattr(order, a, None) not in (None, "") for a in _CAPTURE_MARKER_ATTRS)
    invoice = getattr(order, "amount_paid_ngn", None)
    if invoice is None:
        return None, "none"
    if has_marker:
        return float(invoice), "capture_marker"
    return float(invoice), "invoice_fallback"


def _reference_for(order: Any) -> Optional[str]:
    """The reference the gateway actually charged.

    `tx_ref` is the charged reference (item 1, t_d37da1c4); `payment_reference`
    is the legacy column and is all the 46 legacy `refunded` rows have.
    """
    return getattr(order, "tx_ref", None) or getattr(order, "payment_reference", None)


async def _refund_paystack(reference: str, amount_ngn: float, reason: str) -> GatewayRefund:
    from app.services.paystack import PaystackRefundError, refund_paystack_transaction

    try:
        data = await refund_paystack_transaction(reference, amount_ngn, reason=reason)
    except PaystackRefundError as e:
        raise GatewayRefundError(f"Paystack refund failed: {e}") from e
    return GatewayRefund(
        provider="paystack",
        gateway_refund_id=str(data.get("id")),
        gateway_status=str(data.get("status") or "success"),
        reference=reference,
        amount_ngn=amount_ngn,
    )


async def _refund_flutterwave(reference: str, amount_ngn: float, reason: str) -> GatewayRefund:
    from app.services.flutterwave import _flutterwave_refund

    settings = get_settings()
    if not settings.flutterwave_secret_key:
        raise GatewayRefundError("Flutterwave gateway is not configured (no secret key)")
    try:
        body = await _flutterwave_refund(reference, amount_ngn, settings.flutterwave_secret_key)
    except Exception as e:
        raise GatewayRefundError(f"Flutterwave refund failed: {e}") from e

    data = (body or {}).get("data") or {}
    refund_id = data.get("id")
    if not refund_id:
        raise GatewayRefundError(
            "Flutterwave refund response carried no refund id — refusing to mark the order refunded"
        )
    return GatewayRefund(
        provider="flutterwave",
        gateway_refund_id=str(refund_id),
        gateway_status=str(data.get("status") or "SUCCESSFUL"),
        reference=reference,
        amount_ngn=amount_ngn,
    )


async def refund_at_gateway(
    order: Any,
    *,
    reason: str,
    provider: Optional[str] = None,
    amount_ngn: Optional[float] = None,
    allow_invoice_fallback: bool = True,
) -> GatewayRefund:
    """Refund `order` at its gateway and return the gateway's refund id.

    Raises `GatewayRefundError` unless the gateway confirmed. Callers must treat
    a raise as "money did not move" and leave the order actionable.
    """
    provider_name = (provider or getattr(order, "provider", None) or "").strip().lower()
    if not provider_name:
        raise GatewayRefundError(
            "order has no provider recorded — cannot choose a gateway to refund through"
        )
    if provider_name not in SUPPORTED_PROVIDERS:
        raise GatewayRefundError(f"unsupported refund provider '{provider_name}'")

    reference = _reference_for(order)
    if not reference:
        raise GatewayRefundError(
            "order has no gateway reference (tx_ref/payment_reference) — there is no "
            "transaction to refund, so a refund cannot be verified against the gateway"
        )

    if amount_ngn is None:
        captured, source = _resolve_captured_amount(order)
        if captured is None:
            raise GatewayRefundError(
                "no captured amount on this order — amount_paid_ngn is an invoice amount, "
                "not proof money arrived, so the refund amount cannot be established"
            )
        if source == "invoice_fallback" and not allow_invoice_fallback:
            raise GatewayRefundError(
                "no capture record on this order; refusing to refund on the invoice amount"
            )
        if source == "invoice_fallback":
            logger.warning(
                "refund for order %s using INVOICE amount %s — no capture record exists "
                "(capture column lands with t_c0b38088); amount is not gateway-confirmed",
                getattr(order, "order_id", "?"),
                captured,
            )
        amount_ngn = captured

    amount_ngn = float(amount_ngn or 0)
    if amount_ngn <= 0:
        raise GatewayRefundError(f"refund amount must be > 0 (got {amount_ngn})")

    if provider_name == "paystack":
        return await _refund_paystack(reference, amount_ngn, reason)
    return await _refund_flutterwave(reference, amount_ngn, reason)
