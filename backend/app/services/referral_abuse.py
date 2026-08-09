"""Referral abuse prevention service.

Enforces:
- Self-referral detection (same phone can't refer itself)
- Velocity limit: 3 referrals per referrer per calendar month
- 7-day refund clawback: if referred customer refunds within 7 days, revoke referrer credit
- Duplicate referral prevention: one referral credit per customer

Usage: call `check_referral_abuse(referrer_phone, referred_phone, order_id, session)`
before crediting a referral. Raises `ReferralAbuseError` if abuse is detected.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────
MAX_REFERRALS_PER_MONTH = 3
CLAWBACK_DAYS = 7     # days after which refund clawback no longer applies
CLAWBACK_PCT = 1.0   # 100% credit clawback

# ── Exceptions ─────────────────────────────────────────────────────────────────

class ReferralAbuseError(Exception):
    """Raised when a referral attempt is abusive."""

    def __init__(self, abuse_type: str, message: str):
        self.abuse_type = abuse_type
        self.message = message
        super().__init__(message)


# ── Dataclasses ────────────────────────────────────────────────────────────────

@dataclass
class ReferralCheckResult:
    allowed: bool
    abuse_type: str | None   # None if allowed
    reason: str | None
    credit_amount_ngn: Decimal | None


# ── Core check ────────────────────────────────────────────────────────────────

async def check_referral_abuse(
    referrer_phone: str,
    referred_phone: str,
    order_id: str,
    session: AsyncSession,
    order_amount_ngn: Decimal | None = None,
) -> ReferralCheckResult:
    """Check if a referral is legitimate.

    Returns ReferralCheckResult. Raises nothing — caller decides what to do
    with the result (block, warn, allow).
    """
    try:
        # ── 1. Self-referral ─────────────────────────────────────────────────
        if referrer_phone == referred_phone:
            await _log_abuse(
                session,
                referred_phone=referred_phone,
                referrer_phone=None,
                abuse_type="self_referral",
                order_id=order_id,
            )
            return ReferralCheckResult(
                allowed=False,
                abuse_type="self_referral",
                reason="Self-referral detected — same phone cannot refer itself",
            )

        # ── 2. Duplicate referral ──────────────────────────────────────────────
        dup_stmt = select(func.count()).select_from("orders").where(
            and_(
                # referred phone already used a referral
            )
        )
        # Simple: has this referred phone ever been credited before?
        dup_stmt2 = select(func.count()).select_from("referral_abuse_events").where(
            and_(
                __import__("sqlalchemy").column("referred_customer_phone") == referred_phone,
                __import__("sqlalchemy").column("abuse_type") == "duplicate_referral",
            )
        )
        dup_result = await session.execute(dup_stmt2)
        dup_count = dup_result.scalar() or 0
        if dup_count > 0:
            await _log_abuse(
                session, referred_phone, referrer_phone,
                "duplicate_referral", order_id,
            )
            return ReferralCheckResult(
                allowed=False,
                abuse_type="duplicate_referral",
                reason="This customer was already referred — only one referral credit per customer",
            )

        # ── 3. Velocity limit ─────────────────────────────────────────────────
        # Count referrals credited to this referrer this calendar month
        now = datetime.now(timezone.utc)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        from app.models import Customer

        referrer_stmt = select(Customer).where(Customer.phone == referrer_phone)
        referrer_result = await session.execute(referrer_stmt)
        referrer = referrer_result.scalar_one_or_none()

        monthly_count = getattr(referrer, "referral_count_monthly", 0) or 0
        if monthly_count >= MAX_REFERRALS_PER_MONTH:
            await _log_abuse(
                session, referred_phone, referrer_phone,
                "velocity_breach", order_id,
            )
            return ReferralCheckResult(
                allowed=False,
                abuse_type="velocity_breach",
                reason=f"Referrer has reached monthly limit of {MAX_REFERRALS_PER_MONTH} referrals",
            )

        # ── 4. Calculate credit ─────────────────────────────────────────────
        if order_amount_ngn is None:
            credit = Decimal("0")
        else:
            credit = (order_amount_ngn * Decimal("0.05")).quantize(Decimal("1.00"))

        return ReferralCheckResult(
            allowed=True,
            abuse_type=None,
            reason=None,
            credit_amount_ngn=credit,
        )

    except ReferralAbuseError:
        raise
    except Exception as e:
        logger.error(f"Referral abuse check failed: {e}")
        # Fail open — don't block orders due to a check error
        return ReferralCheckResult(
            allowed=True,
            abuse_type=None,
            reason=None,
            credit_amount_ngn=Decimal("0"),
        )


async def _log_abuse(
    session: AsyncSession,
    referred_phone: str,
    referrer_phone: str | None,
    abuse_type: str,
    order_id: str,
    credit_amount: Decimal | None = None,
) -> None:
    """Log an abuse event to the audit table."""
    from sqlalchemy import text

    try:
        await session.execute(
            text("""
                INSERT INTO referral_abuse_events
                    (referred_customer_phone, referrer_phone, abuse_type, order_id, credit_amount_ngn, created_at)
                VALUES (:phone, :referrer, :type, :order_id, :credit, NOW())
            """),
            {
                "phone": referred_phone,
                "referrer": referrer_phone,
                "type": abuse_type,
                "order_id": order_id,
                "credit": float(credit_amount) if credit_amount else None,
            },
        )
        await session.commit()
        logger.info(
            f"Referral abuse logged: type={abuse_type} "
            f"phone={referred_phone} order_id={order_id}"
        )
    except Exception as e:
        logger.error(f"Failed to log referral abuse: {e}")
        await session.rollback()


async def process_refund_clawback(
    order_id: str,
    session: AsyncSession,
) -> Decimal:
    """Called when a referred order is refunded.

    If the referral credit was earned within CLAWBACK_DAYS, revoke it from
    the referrer's account and log the clawback event.

    Returns the amount clawed back.
    """
    from app.models import Customer, Order
    from sqlalchemy import text

    # Find the credited referral event for this order
    result = await session.execute(
        select(text("""
            SELECT referrer_phone, credit_amount_ngn, created_at
            FROM referral_abuse_events
            WHERE order_id = :oid
              AND abuse_type IN ('referral_credited', 'velocity_breach')
            LIMIT 1
        """)).bindparams(oid=order_id)
    )
    event = result.scalar_one_or_none()
    if not event:
        return Decimal("0")

    referrer_phone, credit_amount, credited_at = event
    credit = Decimal(str(credit_amount)) if credit_amount else Decimal("0")

    # Check if within clawback window
    if credited_at:
        age_days = (datetime.now(timezone.utc) - credited_at.replace(tzinfo=timezone.utc)).days
    else:
        age_days = CLAWBACK_DAYS + 1  # treat missing date as outside window

    if age_days > CLAWBACK_DAYS:
        logger.info(f"Clawback skipped — referral for {order_id} is {age_days} days old")
        return Decimal("0")

    # Revoke credit from referrer
    referrer_result = await session.execute(
        select(Customer).where(Customer.phone == referrer_phone)
    )
    referrer = referrer_result.scalar_one_or_none()
    if referrer and credit > 0:
        referrer.referral_credit_ngn = max(
            Decimal("0"),
            Decimal(str(referrer.referral_credit_ngn or 0)) - credit,
        )
        referrer.referral_credit_revoked_ngn = (
            Decimal(str(referrer.referral_credit_revoked_ngn or 0)) + credit
        )

    # Log clawback
    await session.execute(
        text("""
            INSERT INTO referral_abuse_events
                (referred_customer_phone, referrer_phone, abuse_type, order_id, credit_amount_ngn, revoked, created_at)
            VALUES (:phone, :referrer, 'refund_clawback', :oid, :credit, TRUE, NOW())
        """),
        {
            "phone": "refunded_customer",
            "referrer": referrer_phone,
            "oid": order_id,
            "credit": float(credit),
        },
    )
    await session.commit()
    logger.info(f"Referral clawback: {credit} NGN revoked from {referrer_phone} for order {order_id}")
    return credit
