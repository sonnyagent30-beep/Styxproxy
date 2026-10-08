"""Payment CAPTURE evidence — the authoritative answer to "did they pay?".

## Why this module exists

`orders.amount_paid_ngn` is an **invoice** amount. It is written at order
creation, before any money moves, and it is populated on 100% of production
rows — including every `cancelled`, `refunded` and `expired` one (46 refunded,
54 cancelled, 110 expired at the time of writing). Summing it gives you what we
*asked for*, never what we *received*.

There was no column anywhere in the schema that recorded the money actually
arriving, so once live keys were installed the central operational question
("may I provision? is this refundable? what did we take in?") could only be
answered by calling the gateway per transaction — which is exactly what makes
bulk reconciliation impractical.

This module is the single write path for capture evidence, so that no future
call site can invent its own convention and so that the rules below hold
everywhere:

  1. `provider` is mandatory on every capture record. It is NULL on all 19
     historical `fulfilled` and all 8 `active` rows — written by hand or by
     test, never by a webhook. A capture row with no provider cannot be
     reconciled against anybody, so `record_capture` refuses to write one.
  2. The amount stored is the amount **the gateway says it charged**, taken
     from the gateway's own response. It is never re-derived from local
     arithmetic. This matters because the two gateways use opposite amount
     conventions and getting it wrong under- or over-charges by 100x:
       - Paystack `amount` is the SUBUNIT (kobo)  -> divide by 100
       - Flutterwave v3 `amount` is the MAJOR unit (NGN) -> do NOT divide
     `record_capture` therefore takes an explicit unit argument rather than
     guessing.
  3. `captured_at` is set only when money actually arrived (`success`). A
     `pending` record has a null `captured_at` by construction, so
     "was it captured?" cannot be answered by a row that was merely opened.
  4. Nothing may mark a `cancelled` or `refunded` order as captured. Those
     rows carry an invoice amount but are not evidence of payment.

## Which local statuses disqualify a capture, and why only those two

`orders.status` is OUR workflow state; `orders.gateway_status` is the
GATEWAY's statement about money. Only the second answers "did they pay?", so
the capture test keys off it and uses the local status solely as a veto on two
specific statuses:

  * `cancelled` — no payment was ever intended to complete.
  * `refunded` — admin._process_refund() flips this WITHOUT calling the
    gateway (gate item 3, t_f765263b), so it can describe money the gateway
    still holds. Once that card lands and the flip only happens post-confirmation,
    `gateway_status` will already say `refunded` and this veto becomes belt-and-braces.

Every other local status — `pending`, `expired`, `failed_unfulfilled`, or
anything else — still counts as captured when the gateway says success, and
that is deliberate:

  * `expired`: the webhooks reject an expired order with 400 before recording
    anything, so a customer who paid after the TTL lapsed leaves the gateway
    holding their money. If a capture record ever does land for such a row it
    must read as captured, or that customer becomes unrefundable precisely
    because we let the order expire.
  * `failed_unfulfilled`: charged but undeliverable — the row that most needs a
    refund, and the one item 3 reads `gateway_amount_ngn` from. Hiding it would
    make the worst-funded orders the hardest to refund.

Vetoing those statuses would mean deciding that money we demonstrably hold does
not count as captured, which reintroduces the very unreliability this module
exists to remove.

## Reading capture evidence

Use `was_captured()` / `capture_query()` rather than testing `status` or
`amount_paid_ngn` by hand. `capture_query()` deliberately excludes
`cancelled`/`refunded` rows: today `admin._process_refund()` flips status to
`refunded` without ever calling the gateway (gate item 3, card t_f765263b), so
a row can say `refunded` while the gateway still holds the money. Both the
gateway status and the local status must agree before we call it captured.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import ColumnElement

logger = logging.getLogger(__name__)


# ── The gateway-status vocabulary ─────────────────────────────────────────────
# Stored in `orders.gateway_status`. This is the GATEWAY's view of the money,
# distinct from `orders.status`, which is our own workflow state.
GATEWAY_STATUS_PENDING = "pending"
GATEWAY_STATUS_SUCCESS = "success"
GATEWAY_STATUS_FAILED = "failed"
GATEWAY_STATUS_REFUNDED = "refunded"

GATEWAY_STATUSES = frozenset({
    GATEWAY_STATUS_PENDING,
    GATEWAY_STATUS_SUCCESS,
    GATEWAY_STATUS_FAILED,
    GATEWAY_STATUS_REFUNDED,
})

# The only status in which money has actually arrived.
CAPTURED_STATUS = GATEWAY_STATUS_SUCCESS

# Amount units, per gateway. Stated explicitly at every call site because the
# two disagree and the mistake is silent (it under/over-charges by 100x).
UNIT_MAJOR = "major"  # Flutterwave v3, NOWPayments — naira
UNIT_MINOR = "minor"  # Paystack — kobo

# A local status of cancelled/refunded is never proof of capture. `refunded`
# in particular is currently written by an admin path that never calls the
# gateway, so it can describe money the gateway still holds.
NON_CAPTURE_ORDER_STATUSES = ("cancelled", "refunded")


class CaptureContractError(ValueError):
    """Raised when a caller tries to write a capture record we cannot trust.

    Raised instead of silently writing a half-populated row: a fabricated
    capture record is worse than a null one, because it reads as evidence.
    """


def gateway_captured_at(payload: dict) -> Optional[datetime]:
    """Extract the capture timestamp from a gateway payload, or None.

    Gateways name and format this differently (Paystack: `paid_at` epoch
    seconds; Flutterwave: `created_at` ISO-8601). Reading the gateway's own
    timestamp — rather than stamping `datetime.now()` at webhook arrival — keeps
    `captured_at` meaning "when the gateway says the money arrived", which is
    what makes period-by-period revenue figures defensible. Webhook delivery is
    routinely delayed, and a row stamped on arrival silently shifts revenue
    across a day boundary.

    Returns None if nothing parseable is present; the caller then falls back to
    arrival time, which is a weaker but still truthful claim.
    """
    if not isinstance(payload, dict):
        return None
    raw = (
        payload.get("paid_at")
        or payload.get("created_at")
        or payload.get("createdAt")
        or payload.get("paidAt")
    )
    if raw is None:
        return None
    try:
        if isinstance(raw, (int, float)):
            # Epoch seconds, or milliseconds if implausibly large.
            seconds = raw / 1000.0 if raw > 1e12 else float(raw)
            return datetime.fromtimestamp(seconds, tz=timezone.utc)
        cleaned = str(raw).replace("Z", "+00:00")
        parsed = datetime.fromisoformat(cleaned)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError, OSError):
        return None


def normalise_gateway_amount(amount: float | int | None, unit: str) -> Optional[float]:
    """Convert a gateway-supplied amount to naira (major unit).

    `amount` must be the value the GATEWAY reported, never a locally computed
    one. `unit` says how that gateway expresses it. Raises rather than guessing:
    a caller that does not know its gateway's convention must not invent one.
    """
    if amount is None:
        return None
    if unit == UNIT_MINOR:
        return round(float(amount) / 100.0, 2)
    if unit == UNIT_MAJOR:
        return round(float(amount), 2)
    raise CaptureContractError(
        f"unknown amount unit {unit!r} — pass {UNIT_MAJOR!r} (Flutterwave/NOWPayments, "
        f"naira) or {UNIT_MINOR!r} (Paystack, kobo). Guessing here mischarges by 100x."
    )


def record_capture(
    order,
    *,
    provider: Optional[str],
    gateway_status: str,
    gateway_amount: float | int | None = None,
    amount_unit: Optional[str] = None,
    gateway_reference: Optional[str] = None,
    gateway_currency: Optional[str] = None,
    captured_at: Optional[datetime] = None,
    gateway_transaction_id: Optional[str] = None,
) -> None:
    """Write gateway capture evidence onto `order` (mutates, does not commit).

    The caller commits. Every payment path — payment-init and each webhook —
    goes through here so the invariants hold without relying on each call site
    remembering them.

    Args:
        order: the `Order` row to annotate.
        provider: gateway name, e.g. "paystack" / "flutterwave". REQUIRED.
        gateway_status: one of GATEWAY_STATUSES.
        gateway_amount: the amount the gateway reported it charged, in
            `amount_unit`. None is allowed only for `pending`.
        amount_unit: UNIT_MAJOR or UNIT_MINOR. Required when an amount is given.
        gateway_reference: the reference the gateway itself echoed/charged.
        gateway_currency: ISO code as the gateway reported it, when known.
        captured_at: when the money arrived. Defaults to now for `success`,
            and is forced to None otherwise — a `pending` row must never look
            captured.
        gateway_transaction_id: the gateway's own numeric transaction id.

    Raises:
        CaptureContractError: on a missing provider, an unknown status, an
            amount with no unit, or an attempt to mark a cancelled/refunded
            order as captured.
    """
    if not provider or not str(provider).strip():
        raise CaptureContractError(
            "refusing to write a capture record without a provider — it could not be "
            "reconciled against any gateway. (Every historical `fulfilled`/`active` "
            "row has provider=NULL, written by hand or by test, never a webhook.)"
        )
    provider = str(provider).strip().lower()

    if gateway_status not in GATEWAY_STATUSES:
        raise CaptureContractError(
            f"unknown gateway_status {gateway_status!r}; expected one of "
            f"{sorted(GATEWAY_STATUSES)}"
        )

    normalised = None
    if gateway_amount is not None:
        if amount_unit is None:
            raise CaptureContractError(
                "gateway_amount given without amount_unit — Paystack reports kobo and "
                "Flutterwave reports naira, so the unit must be stated, not assumed"
            )
        normalised = normalise_gateway_amount(gateway_amount, amount_unit)
    elif gateway_status == CAPTURED_STATUS:
        raise CaptureContractError(
            f"gateway_status={CAPTURED_STATUS!r} requires gateway_amount — the amount "
            "the gateway charged, taken from its own response. Without it this row "
            "cannot answer 'how much did they actually pay?'."
        )

    if gateway_status == CAPTURED_STATUS and order.status in NON_CAPTURE_ORDER_STATUSES:
        raise CaptureContractError(
            f"order {getattr(order, 'order_id', '?')} has local status "
            f"{order.status!r} — refusing to mark it as captured. A cancelled or "
            "refunded order carries an invoice amount, not evidence of payment."
        )

    # captured_at is meaningful only for money that actually arrived.
    if gateway_status == CAPTURED_STATUS:
        order.captured_at = captured_at or datetime.now(timezone.utc)
    else:
        order.captured_at = None

    order.provider = provider
    order.gateway_status = gateway_status
    order.gateway_amount_ngn = normalised
    order.gateway_currency = gateway_currency
    if gateway_reference:
        order.gateway_reference = gateway_reference
    if gateway_transaction_id:
        order.provider_order_id = str(gateway_transaction_id)

    logger.info(
        "capture recorded",
        extra={
            "order_id": getattr(order, "order_id", None),
            "provider": provider,
            "gateway_status": gateway_status,
            # Log the invoiced amount alongside so a divergence between what we
            # billed and what the gateway took is visible in the logs.
            "gateway_amount_ngn": normalised,
            "invoiced_amount_ngn": (
                float(order.amount_paid_ngn) if order.amount_paid_ngn is not None else None
            ),
        },
    )


def was_captured(order) -> bool:
    """True only if this row is evidence that money actually arrived.

    Requires the gateway to say `success`, a non-null `captured_at`, a gateway
    to attribute the charge to, a captured amount, AND a local status that is
    not cancelled/refunded. Any one of those missing means we cannot prove it
    from our own database.
    """
    if order is None:
        return False
    return (
        getattr(order, "gateway_status", None) == CAPTURED_STATUS
        and getattr(order, "captured_at", None) is not None
        and getattr(order, "gateway_amount_ngn", None) is not None
        and getattr(order, "provider", None) is not None
        and getattr(order, "status", None) not in NON_CAPTURE_ORDER_STATUSES
    )


def capture_query() -> ColumnElement[bool]:
    """SQL predicate matching exactly the rows `was_captured()` accepts.

    Use this for the questions that actually matter operationally — which
    orders may be provisioned, which are refundable, what did we take in this
    period. It is the same predicate, so a bulk query can never disagree with
    the row-by-row check.

    Never widen this to `amount_paid_ngn IS NOT NULL` or `status = 'paid'`.
    """
    from app.models import Order

    return (
        (Order.gateway_status == CAPTURED_STATUS)
        & (Order.captured_at.isnot(None))
        & (Order.gateway_amount_ngn.isnot(None))
        & (Order.provider.isnot(None))
        & (Order.status.notin_(NON_CAPTURE_ORDER_STATUSES))
    )


def captured_revenue_stmt(since=None, until=None):
    """Sum of money the GATEWAYS say we actually took, for a period.

    Built on `gateway_amount_ngn` (the gateway's own charged figure) over
    `captured_at` (the gateway's own capture time) — never `amount_paid_ngn`
    grouped by `created_at`, which counts invoices that were never paid and
    dates them to when the order was raised.

    IMPORTANT — read before wiring this to a dashboard: every pre-existing
    order has `captured_at = NULL`, because the schema had no way to record
    capture and a fabricated backfill would be worse than a null. This
    function therefore reports **zero for all historical revenue** and only
    becomes correct for orders placed after the capture columns shipped.

    That is the honest number, not a bug. Switching a live revenue dashboard to
    it today would visibly report N0, so whoever does that switch needs Finance
    to agree the presentation (show captured-only, or show captured alongside
    invoiced) before it ships. Do not paper over the gap by summing
    `amount_paid_ngn` "until the data catches up" — that is the exact confusion
    this module exists to end.
    """
    from sqlalchemy import func, select

    from app.models import Order

    stmt = select(func.coalesce(func.sum(Order.gateway_amount_ngn), 0)).where(capture_query())
    if since is not None:
        stmt = stmt.where(Order.captured_at >= since)
    if until is not None:
        stmt = stmt.where(Order.captured_at < until)
    return stmt
