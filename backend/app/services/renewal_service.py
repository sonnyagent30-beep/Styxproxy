"""Renewal service — handles proxy subscription renewals.

For residential/mobile plans: creates a new credential for the extra GB.
For DC/ISP plans: only extends the expiry (no GB involved).

Stacking rule: new expiry = renewal_date + 30 days (NOT current_expiry + 30).
Unlimited renewals per order.
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Order, OrderRenewal, StyxproxyCredential
from app.services.credential import create_credential, resolve_country_for_credential

logger = logging.getLogger(__name__)

RENEWAL_DURATION_DAYS = 30


async def create_renewal_order(
    session: AsyncSession,
    order_id: str,
    quantity_gb: Optional[float],
    amount_paid_ngn: float,
    payment_reference: Optional[str] = None,
    tx_ref: Optional[str] = None,
) -> OrderRenewal:
    """Create a renewal record for an order.

    The renewal starts as 'pending' and is completed by the fulfillment flow
    (webhook → worker → credential creation / expiry extension).
    """
    renewal = OrderRenewal(
        order_id=order_id,
        renewal_tx_ref=tx_ref or f"TXR-{uuid.uuid4().hex[:12].upper()}",
        quantity_gb=quantity_gb,
        amount_paid_ngn=amount_paid_ngn,
        payment_reference=payment_reference,
        status="pending",
    )
    session.add(renewal)
    await session.commit()
    await session.refresh(renewal)
    logger.info(
        "Renewal order created: id=%s order_id=%s gb=%s amount=%s",
        renewal.id, order_id, quantity_gb, amount_paid_ngn,
    )
    return renewal


async def complete_renewal_residential_mobile(
    session: AsyncSession,
    renewal: OrderRenewal,
    order: Order,
) -> Optional[StyxproxyCredential]:
    """Complete a residential/mobile renewal by creating a new credential for the extra GB.

    Returns the new credential, or None on failure.
    """
    if not renewal.quantity_gb or renewal.quantity_gb <= 0:
        logger.error(
            "Renewal %s has no quantity_gb — cannot create credential",
            renewal.id,
        )
        return None

    try:
        credential, _ = await create_credential(
            db_session=session,
            order_id=order.order_id,
            customer_phone=order.customer_phone or "",
            plan_code=order.plan_code or "unknown",
            country=resolve_country_for_credential(order.country),
            proxy_type=order.plan_type or "residential",
            quantity=int(renewal.quantity_gb),
            duration_days=RENEWAL_DURATION_DAYS,
            protocol="socks5",
            pool_type="paid",
            targeting_mode=order.targeting_mode or "country_chosen",
            city=order.city_name,
        )

        # Update order's data_remaining_gb (add the new GB)
        current_remaining = float(order.data_remaining_gb or 0)
        order.data_remaining_gb = current_remaining + float(renewal.quantity_gb)

        # Extend expiry: renewal_date + 30 days (stack from renewal date, not current expiry)
        new_expiry = datetime.now(timezone.utc) + timedelta(days=RENEWAL_DURATION_DAYS)
        order.expires_at = new_expiry

        renewal.credential_id = credential.id
        renewal.expires_at = new_expiry
        renewal.status = "completed"
        await session.commit()
        await session.refresh(renewal)

        logger.info(
            "Renewal %s completed: credential_id=%s new_expiry=%s",
            renewal.id, credential.id, new_expiry,
        )
        return credential

    except Exception as e:
        logger.error("Renewal %s failed: %s", renewal.id, e, exc_info=True)
        renewal.status = "failed"
        await session.commit()
        return None


async def complete_renewal_dc_isp(
    session: AsyncSession,
    renewal: OrderRenewal,
    order: Order,
) -> bool:
    """Complete a DC/ISP renewal by extending the expiry.

    No credential creation needed — DC/ISP plans don't have GB.
    """
    try:
        new_expiry = datetime.now(timezone.utc) + timedelta(days=RENEWAL_DURATION_DAYS)
        order.expires_at = new_expiry
        renewal.expires_at = new_expiry
        renewal.status = "completed"
        await session.commit()
        await session.refresh(renewal)

        logger.info(
            "Renewal %s completed (DC/ISP): new_expiry=%s",
            renewal.id, new_expiry,
        )
        return True

    except Exception as e:
        logger.error("Renewal %s failed: %s", renewal.id, e, exc_info=True)
        renewal.status = "failed"
        await session.commit()
        return False


async def get_renewals_for_order(
    session: AsyncSession,
    order_id: str,
) -> list[OrderRenewal]:
    """Get all renewals for an order, newest first."""
    result = await session.execute(
        select(OrderRenewal)
        .where(OrderRenewal.order_id == order_id)
        .order_by(OrderRenewal.created_at.desc())
    )
    return list(result.scalars().all())


async def get_renewal_by_payment_reference(
    session: AsyncSession,
    payment_reference: str,
) -> Optional[OrderRenewal]:
    """Look up a renewal by its payment reference."""
    result = await session.execute(
        select(OrderRenewal).where(OrderRenewal.payment_reference == payment_reference)
    )
    return result.scalar_one_or_none()
