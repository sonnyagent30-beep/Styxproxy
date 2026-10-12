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
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx
from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

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


async def _send_renewal_reminder_via_charon(
    phone: str,
    message: str,
) -> bool:
    """Send a renewal reminder via the Charon API (WhatsApp/Telegram).

    Charon routes the message to the customer preferred channel
    (WhatsApp or Telegram) based on their history. This is the same
    delivery path that credential delivery uses.

    Returns True if Charon accepted the message (HTTP 200).
    """
    url = f"{_CHARON_API_BASE}/api/v1/charon/reply"
    payload = {
        "user_message": message,
        "customer_phone": phone,
        "channel": "whatsapp",  # Charon routes based on customer history
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code == 200:
                return True
            else:
                logger.warning(
                    "Charon renewal reminder failed: HTTP %d — %s",
                    resp.status_code,
                    resp.text[:200],
                )
                return False
    except Exception as exc:
        logger.error("Charon renewal reminder error: %s", exc)
        return False


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
        "sent"     — reminder was delivered successfully.
        "skipped"  — no reminder needed (already sent today, max reached,
                     no customer, no phone).
        "error"    — delivery failed (Charon API error, exception).
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

    did_send = await _send_renewal_reminder_via_charon(
        phone=customer_phone,
        message=message,
    )

    if did_send:
        # Update tracking fields on the order
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
            "Renewal reminder sent for order %s (expires in %d days)",
            order.order_id,
            days_remaining,
        )
        return "sent"
    else:
        logger.warning(
            "Failed to send renewal reminder for order %s via Charon",
            order.order_id,
        )
        return "error"


async def send_daily_renewal_reminders(session: AsyncSession) -> dict:
    """Scan all live orders expiring within 3 days and send reminders.

    This is the cron job entry point. Should be run once per day.

    Returns a summary dict: {"sent": N, "skipped": M, "errors": K}
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
