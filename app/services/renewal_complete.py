"""Complete a pending renewal — extend the existing credential's expiry and data.

Called by the webhook handler when a renewal payment is confirmed.
Stacking rule: new expiry = renewal_date + 30 days (NOT current_expiry + 30).
Unlimited renewals per order. Never issues a second proxy.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Order, OrderRenewal, ProxyItem, StyxproxyCredential

logger = logging.getLogger(__name__)

RENEWAL_DURATION_DAYS = 30


async def complete_renewal(
    session: AsyncSession,
    renewal_id: int,
) -> Optional[OrderRenewal]:
    """Complete a pending renewal — extend the existing credential.

    Returns the completed renewal, or None if not found / already completed.
    """
    renewal = (
        await session.execute(select(OrderRenewal).where(OrderRenewal.id == renewal_id))
    ).scalar_one_or_none()

    if not renewal:
        logger.warning("Renewal %s not found", renewal_id)
        return None

    if renewal.status != "pending":
        logger.info("Renewal %s already %s — skipping", renewal.id, renewal.status)
        return renewal

    order = (
        await session.execute(select(Order).where(Order.order_id == renewal.order_id))
    ).scalar_one_or_none()

    if not order:
        logger.error("Order %s not found for renewal %s", renewal.order_id, renewal.id)
        renewal.status = "failed"
        await session.commit()
        return None

    # Get the existing credential
    if not order.styxproxy_credential_id:
        logger.error("Order %s has no credential to renew", order.order_id)
        renewal.status = "failed"
        await session.commit()
        return None

    cred = (
        await session.execute(
            select(StyxproxyCredential).where(
                StyxproxyCredential.id == order.styxproxy_credential_id
            )
        )
    ).scalar_one_or_none()

    if not cred:
        logger.error(
            "Credential %s not found for order %s",
            order.styxproxy_credential_id,
            order.order_id,
        )
        renewal.status = "failed"
        await session.commit()
        return None

    now = datetime.now(timezone.utc)
    new_expiry = now + timedelta(days=RENEWAL_DURATION_DAYS)

    # Extend credential expiry (always)
    cred.expires_at = new_expiry

    # Extend order expiry (always)
    order.expires_at = new_expiry

    # If per-item renewal, update the proxy_item
    if renewal.proxy_item_id:
        proxy_item = await session.get(ProxyItem, renewal.proxy_item_id)
        if proxy_item:
            proxy_item.expires_at = new_expiry
            proxy_item.status = "active"

    # Extend data expiry for per-GB plans
    if renewal.quantity_gb > 0:
        # Add GB to remaining data
        current_remaining = float(order.data_remaining_gb or 0)
        order.data_remaining_gb = current_remaining + renewal.quantity_gb

        # Also update total if it exists
        if order.data_total_gb is not None:
            current_total = float(order.data_total_gb)
            order.data_total_gb = current_total + renewal.quantity_gb

        # Extend data_expires to match
        order.data_expires = new_expiry

    # Mark renewal as fulfilled
    renewal.status = "fulfilled"
    renewal.fulfilled_at = now

    await session.commit()
    logger.info(
        "Renewal %s completed: order=%s cred=%d new_expiry=%s +%dGB proxy_item_id=%s",
        renewal.id,
        order.order_id,
        cred.id,
        new_expiry.isoformat(),
        renewal.quantity_gb,
        renewal.proxy_item_id,
    )

    return renewal
