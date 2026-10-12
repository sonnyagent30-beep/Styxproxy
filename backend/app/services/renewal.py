"""Renewal reminder service — S2.5 (BIZ STYXv2-004 §4.2 Sprint 3).

Sends renewal reminders via Charon (WhatsApp/Telegram) when a proxy
subscription is about to expire. Styxproxy is a phone-first business —
customers give a phone number, not an email. Delivery goes through the
same Charon API path that credential delivery uses.

Supports two trigger mechanisms:
  1. Daily cron job — scans all live orders expiring within 3 days.
  2. On-access check — fires on any authenticated request for an order that
     is live and within the 3-day warning window but has not yet received
     a reminder today.

Tracks sends in the Order model (emails_sent, reminder_sent_at).

DELIVERY CONTRACT (fixed 2026-10-12):
  Charon's /reply endpoint returns HTTP 200 when it ACCEPTS a message,
  not when WhatsApp delivers it. The old code treated 200 as delivery,
  set reminder_sent_at, and the idempotency guard then suppressed retries.
  Result: sent=0, errors=0, customer never notified, system reported success.

  Now: we check WhatsApp is configured BEFORE attempting send, and only
  mark reminder_sent_at / increment emails_sent on CONFIRMED delivery.
  A failed or unconfirmed send leaves the order eligible for retry.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx
from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import Customer, Order
from app.services.order_status import is_live_order, LIVE_ORDER_STATUSES

logger = logging.getLogger(__name__)

# How many days before expiry to start sending reminders.
RENEWAL_WARNING_DAYS = 3

# How many reminders to send per order (once per day for up to 3 days).
MAX_REMINDERS = 3

# Charon API base — the renewal cron runs on the same server as the API,
# so localhost is the most reliable path (no DNS, no TLS, no network hop).
_CHARON_API_BASE = "http://localhost:8000"


async def _get_customer_for_order(
    session: AsyncSession, order: Order
) -> Optional[Customer]:
    """Return the Customer record for an order customer_phone."""
    if not order.customer_phone:
        return None
    stmt = select(Customer).where(Customer.phone == order.customer_phone)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


def _build_renewal_message(
    order: Order,
    customer_name: str,
    days_remaining: int,
) -> str:
    """Build the renewal reminder message sent to the customer."""
    plan_code = order.plan_code or "Proxy Plan"
    renewal_link = f"https://styxproxy.com/order/renewal?renew={order.order_id}"

    if days_remaining == 0:
        urgency = "expires TODAY"
    elif days_remaining == 1:
        urgency = "expires TOMORROW"
    else:
        urgency = f"expires in {days_remaining} days"

    return (
        f"Hi {customer_name}, your Styxproxy {plan_code} {urgency}. "
        f"Renew now to keep your proxy active: {renewal_link}"
    )


class SendResult:
    """Result of a delivery attempt.

    Attributes:
        attempted: Whether we tried to send (False if pre-flight check failed).
        delivered: Whether the message was confirmed delivered to the customer.
        reason: Human-readable status for logging and reporting.
    """

    def __init__(self, attempted: bool, delivered: bool, reason: str):
        self.attempted = attempted
        self.delivered = delivered
        self.reason = reason

    @property
    def ok(self) -> bool:
        """True only when delivery is confirmed."""
        return self.delivered


async def _check_whatsapp_configured() -> tuple[bool, str]:
    """Check if WhatsApp delivery is configured.

    Returns (configured, reason). If configured is False, reason explains why.
    """
    settings = get_settings()
    if not settings.whatsapp_access_token:
        return False, "whatsapp_not_configured"
    return True, "ok"


async def _send_renewal_reminder_via_charon(
    phone: str,
    message: str,
) -> SendResult:
    """Send a renewal reminder via the Charon API (WhatsApp/Telegram).

    IMPORTANT: Charon's /reply returns HTTP 200 when it ACCEPTS the message,
    not when the channel provider delivers it. We do NOT treat 200 as
    delivery. Instead, we report the send as attempted-but-unconfirmed
    unless Charon explicitly returns a delivery confirmation.

    Returns a SendResult with attempted/delivered/reason.
    """
    # Pre-flight: don't even attempt if WhatsApp is not configured.
    configured, reason = await _check_whatsapp_configured()
    if not configured:
        logger.warning(
            "Skipping renewal reminder to %s — WhatsApp not configured (%s)",
            phone, reason,
        )
        return SendResult(attempted=False, delivered=False, reason=reason)

    url = f"{_CHARON_API_BASE}/api/v1/charon/reply"
    payload = {
        "user_message": message,
        "customer_phone": phone,
        "channel": "whatsapp",
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code == 200:
                # Charon accepted the message. This is NOT delivery confirmation.
                # Charon does not currently return explicit delivery status in
                # its response, so we must treat this as unconfirmed.
                logger.info(
                    "Charon accepted renewal reminder for %s (HTTP 200) — "
                    "delivery NOT confirmed, order remains eligible for retry",
                    phone,
                )
                return SendResult(
                    attempted=True,
                    delivered=False,
                    reason="charon_accepted_unconfirmed",
                )
            else:
                logger.warning(
                    "Charon renewal reminder failed: HTTP %d — %s",
                    resp.status_code,
                    resp.text[:200],
                )
                return SendResult(
                    attempted=True,
                    delivered=False,
                    reason=f"charon_http_{resp.status_code}",
                )
    except Exception as exc:
        logger.error("Charon renewal reminder error: %s", exc)
        return SendResult(
            attempted=True,
            delivered=False,
            reason=f"charon_exception:{type(exc).__name__}",
        )


async def check_and_send_renewal_reminder(
    session: AsyncSession,
    order: Order,
    customer: Optional[Customer] = None,
) -> str:
    """Check if an order needs a renewal reminder and send it.

    Call this on authenticated requests for a live order that is within
    the 3-day warning window and has not yet received a reminder today.

    Args:
        session: DB session.
        order: The order to check.
        customer: Pre-loaded Customer record (optional, saves a DB lookup).

    Returns:
        "sent"     — reminder was CONFIRMED delivered.
        "skipped"  — no reminder needed (already sent today, max reached,
                     no customer, no phone, WhatsApp not configured).
        "error"    — delivery was attempted but not confirmed.
    """
    # Only live orders with an expiry date qualify.
    # "active" and "fulfilled" both mean the customer has a usable proxy —
    # the webhook sets "fulfilled", admin re-fulfill sets "active".
    if not is_live_order(order.status) or not order.expires_at:
        return "skipped"

    now = datetime.now(timezone.utc)
    expires_at = order.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    # Calculate days remaining
    days_remaining = (expires_at - now).days

    # Must be within the warning window
    if days_remaining > RENEWAL_WARNING_DAYS or days_remaining < 0:
        return "skipped"

    # Do not re-send if we already sent one today (idempotent — protects against
    # duplicate calls from concurrent / overlapping requests)
    if order.reminder_sent_at:
        sent_day = order.reminder_sent_at.date()
        today = now.date()
        if sent_day >= today:
            return "skipped"

    # Load customer if not provided
    if customer is None:
        customer = await _get_customer_for_order(session, order)

    if customer is None:
        logger.warning(
            "Skipping renewal reminder for order %s — no customer record",
            order.order_id,
        )
        return "skipped"

    # Styxproxy is phone-first: customers give a phone number, not an email.
    # The Customer model has no email column at all.
    customer_phone = customer.phone
    if not customer_phone:
        logger.warning(
            "Skipping renewal reminder for order %s — customer has no phone",
            order.order_id,
        )
        return "skipped"

    customer_name = customer.name or "Customer"
    message = _build_renewal_message(order, customer_name, max(days_remaining, 0))

    result = await _send_renewal_reminder_via_charon(
        phone=customer_phone,
        message=message,
    )

    if result.ok:
        # Only now — on CONFIRMED delivery — do we update tracking fields.
        await session.execute(
            update(Order)
            .where(Order.order_id == order.order_id)
            .values(
                emails_sent=Order.emails_sent + 1,
                reminder_sent_at=now,
            )
        )
        await session.commit()
        logger.info(
            "Renewal reminder SENT for order %s (expires in %d days) — %s",
            order.order_id,
            days_remaining,
            result.reason,
        )
        return "sent"
    elif not result.attempted:
        # Pre-flight check failed (e.g. WhatsApp not configured) — not an error.
        logger.warning(
            "Renewal reminder SKIPPED for order %s — %s",
            order.order_id,
            result.reason,
        )
        return "skipped"
    else:
        # Attempted but delivery not confirmed — order remains eligible for retry.
        logger.warning(
            "Renewal reminder NOT CONFIRMED for order %s — %s. "
            "Order remains eligible for retry.",
            order.order_id,
            result.reason,
        )
        return "error"


async def send_daily_renewal_reminders(session: AsyncSession) -> dict:
    """Scan all live orders expiring within 3 days and send reminders.

    This is the cron job entry point. Should be run once per day.

    Returns a summary dict: {"sent": N, "skipped": M, "errors": K}

    Only "sent" means confirmed delivery. "errors" means attempted but not
    confirmed (the order will be retried on the next run).
    """
    now = datetime.now(timezone.utc)
    warning_cutoff = now + timedelta(days=RENEWAL_WARNING_DAYS)

    # Find all live orders with expiry in the warning window that:
    # - have never received a reminder, OR
    # - had their last reminder sent more than 24h ago
    # We use a two-pass approach: first find qualifying orders, then send.
    stmt = (
        select(Order)
        .where(
            and_(
                Order.status.in_(LIVE_ORDER_STATUSES),
                Order.expires_at.isnot(None),
                Order.expires_at <= warning_cutoff,
                Order.expires_at >= now,  # not already expired
            )
        )
        .order_by(Order.expires_at)
    )

    result = await session.execute(stmt)
    orders = result.scalars().all()

    sent = 0
    skipped = 0
    errors = 0

    for order in orders:
        # Skip if reminder already sent today (same-day protection)
        if order.reminder_sent_at:
            sent_day = order.reminder_sent_at.date()
            today = now.date()
            if sent_day >= today:
                skipped += 1
                continue

        # Also skip if we have hit the max reminder cap
        if order.emails_sent >= MAX_REMINDERS:
            skipped += 1
            continue

        customer = await _get_customer_for_order(session, order)

        outcome = await check_and_send_renewal_reminder(
            session=session,
            order=order,
            customer=customer,
        )
        if outcome == "sent":
            sent += 1
        elif outcome == "skipped":
            skipped += 1
        else:
            errors += 1

    logger.info(
        "Daily renewal reminder run complete: sent=%d, skipped=%d, errors=%d",
        sent,
        skipped,
        errors,
    )
    return {"sent": sent, "skipped": skipped, "errors": errors}
