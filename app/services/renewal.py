"""Renewal reminder service — S2.5 (BIZ STYXv2-004 §4.2 Sprint 3).

Sends renewal reminder emails when a proxy subscription is about to expire.
Supports two trigger mechanisms:
  1. Daily cron job — scans all active orders expiring within 3 days.
  2. On-access check — fires on any authenticated request for an order that
     is active and within the 3-day warning window but has not yet received
     a reminder today.

Tracks sends in the Order model (emails_sent, reminder_sent_at).
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Customer, Order
from app.services.email import send_renewal_reminder_email

logger = logging.getLogger(__name__)

# How many days before expiry to start sending reminders.
RENEWAL_WARNING_DAYS = 3

# How many reminder emails to send per order (once per day for up to 3 days).
MAX_REMINDER_EMAILS = 3


async def _get_customer_for_order(
    session: AsyncSession, order: Order
) -> Optional[Customer]:
    """Return the Customer record for an order's customer_phone."""
    if not order.customer_phone:
        return None
    stmt = select(Customer).where(Customer.phone == order.customer_phone)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def check_and_send_renewal_reminder(
    session: AsyncSession,
    order: Order,
    customer: Optional[Customer] = None,
) -> bool:
    """Check if an order needs a renewal reminder and send it.

    Call this on authenticated requests for an active order that is within
    the 3-day warning window and has not yet received a reminder today.

    Args:
        session: DB session.
        order: The order to check.
        customer: Pre-loaded Customer record (optional, saves a DB lookup).

    Returns:
        True if a reminder was sent, False otherwise.
    """
    # Only active orders with an expiry date qualify
    if order.status != "active" or not order.expires_at:
        return False

    now = datetime.now(timezone.utc)
    expires_at = order.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    # Calculate days remaining
    days_remaining = (expires_at - now).days

    # Must be within the warning window
    if days_remaining > RENEWAL_WARNING_DAYS or days_remaining < 0:
        return False

    # Don't re-send if we already sent one today (idempotent — protects against
    # duplicate calls from concurrent / overlapping requests)
    if order.reminder_sent_at:
        sent_day = order.reminder_sent_at.date()
        today = now.date()
        if sent_day >= today:
            return False

    # Load customer if not provided
    if customer is None:
        customer = await _get_customer_for_order(session, order)

    if customer is None:
        logger.warning("Cannot send renewal reminder for order %s — no customer record", order.order_id)
        return False

    customer_email = getattr(customer, "email", None)
    if not customer_email:
        logger.warning(
            "Cannot send renewal reminder for order %s — customer has no email",
            order.order_id,
        )
        return False

    customer_name = customer.name or "Customer"

    try:
        result = await send_renewal_reminder_email(
            customer_email=customer_email,
            customer_name=customer_name,
            order_id=order.order_id,
            plan_code=order.plan_code or "Proxy Plan",
            expires_at=expires_at,
            days_remaining=max(days_remaining, 0),
        )

        if result.success:
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
            return True
        else:
            logger.warning(
                "Failed to send renewal reminder for order %s: %s",
                order.order_id,
                result.error,
            )
            return False

    except Exception as exc:
        logger.error("Exception sending renewal reminder for order %s: %s", order.order_id, exc)
        return False


async def send_daily_renewal_reminders(session: AsyncSession) -> dict:
    """Scan all active orders expiring within 3 days and send reminders.

    This is the cron job entry point. Should be run once per day.

    Returns a summary dict: {"sent": N, "skipped": M, "errors": K}
    """
    now = datetime.now(timezone.utc)
    warning_cutoff = now + timedelta(days=RENEWAL_WARNING_DAYS)

    # Find all active orders with expiry in the warning window that:
    # - have never received a reminder, OR
    # - had their last reminder sent more than 24h ago
    # We use a two-pass approach: first find qualifying orders, then send.
    stmt = (
        select(Order)
        .where(
            and_(
                Order.status == "active",
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

        # Also skip if we've hit the max reminder cap
        if order.emails_sent >= MAX_REMINDER_EMAILS:
            skipped += 1
            continue

        customer = await _get_customer_for_order(session, order)

        did_send = await check_and_send_renewal_reminder(
            session=session,
            order=order,
            customer=customer,
        )
        if did_send:
            sent += 1
        else:
            errors += 1

    logger.info(
        "Daily renewal reminder run complete: sent=%d, skipped=%d, errors=%d",
        sent,
        skipped,
        errors,
    )
    return {"sent": sent, "skipped": skipped, "errors": errors}
