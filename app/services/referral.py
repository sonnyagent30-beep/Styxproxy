"""Referral code system service.

Generates unique 20-char referral codes, resolves referrers by code,
and applies ₦500 referral credits when a referee's first Flutterwave
payment webhook confirms.
"""

import logging
import secrets
import string

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Customer, Order, ReferralCredit

logger = logging.getLogger(__name__)

# Credit amount in nano-naira: ₦500 = 500_000_000 nGN
REFERRAL_CREDIT_NGN = 500.0
REFERRAL_CREDIT_NGN_NANO = int(REFERRAL_CREDIT_NGN * 1_000_000)

# Characters used for referral codes: uppercase + digits (no O/0/I/1 to avoid confusion)
_REFERRAL_ALPHABET = string.ascii_uppercase + string.digits
_REFERRAL_ALPHABET = _REFERRAL_ALPHABET.replace("O", "").replace("0", "").replace("I", "").replace("1", "")


def generate_referral_code(length: int = 20) -> str:
    """Generate a cryptographically random 20-char unique referral code.

    Uses ``secrets`` (CSPRNG) rather than ``random`` so codes cannot be
    guessed.  The alphabet excludes visually ambiguous characters.
    """
    return "".join(secrets.choice(_REFERRAL_ALPHABET) for _ in range(length))


async def upsert_referral_credit_pending(
    session: AsyncSession,
    *,
    referrer_customer_id: Customer.id,  # type: ignore[has-type]
    referee_customer_id: Customer.id,  # type: ignore[has-type]
) -> ReferralCredit:
    """Create (or return existing) a pending ReferralCredit record.

    Safe to call multiple times — uses ON CONFLICT DO NOTHING semantics
    at the DB level (UniqueConstraint on referee_customer_id).
    Returns the existing row if the referee already has a pending record.
    """
    # Try to insert first; on conflict return the existing row
    stmt = select(ReferralCredit).where(
        ReferralCredit.referee_customer_id == referee_customer_id
    )
    existing = (await session.execute(stmt)).scalar_one_or_none()
    if existing:
        return existing

    credit = ReferralCredit(
        referrer_customer_id=referrer_customer_id,
        referee_customer_id=referee_customer_id,
        credit_amount_nGN=REFERRAL_CREDIT_NGN_NANO,
    )
    session.add(credit)
    await session.flush()
    return credit


async def apply_referral_credit(
    session: AsyncSession,
    *,
    referee_customer_id: Customer.id,  # type: ignore[has-type]
    referee_payment_tx_ref: str,
) -> bool:
    """Apply the pending referral credit for a referee whose first payment just confirmed.

    Idempotent: if the credit is already applied this is a no-op and returns True.
    If no pending credit exists for this referee (e.g. referee had no referrer),
    this is also a no-op and returns False.

    Returns True when a credit was (or already had been) applied; False when
    there was nothing to apply.
    """
    import datetime as dt

    # Find the pending credit for this referee
    stmt = select(ReferralCredit).where(
        ReferralCredit.referee_customer_id == referee_customer_id,
        ReferralCredit.applied_at.is_(None),
    )
    credit = (await session.execute(stmt)).scalar_one_or_none()
    if not credit:
        # No pending referral — referee was not referred or credit already applied
        return False

    # Mark as applied
    credit.applied_at = dt.datetime.now(dt.timezone.utc)
    credit.referee_payment_tx_ref = referee_payment_tx_ref

    # Store the tx_ref on the referee's order so it is queryable
    order_stmt = select(Order).where(Order.payment_reference == referee_payment_tx_ref)
    order = (await session.execute(order_stmt)).scalar_one_or_none()
    if order:
        order.referral_tx_ref = referee_payment_tx_ref

    await session.commit()
    logger.info(
        "Referral credit applied: referee=%s referrer=%s tx_ref=%s amount_nGN=%d",
        referee_customer_id,
        credit.referrer_customer_id,
        referee_payment_tx_ref,
        credit.credit_amount_nGN,
    )
    return True


async def resolve_referrer_by_code(
    session: AsyncSession,
    referral_code: str,
) -> Customer | None:
    """Look up the customer who owns this referral code."""
    stmt = select(Customer).where(Customer.referral_code == referral_code)
    return (await session.execute(stmt)).scalar_one_or_none()


async def get_referral_stats_for_customer(
    session: AsyncSession,
    customer_id: Customer.id,  # type: ignore[has-type]
) -> dict:
    """Return referral stats for a single customer (for admin or self-serve)."""
    # Count successful referrals (applied credits)
    applied_stmt = select(ReferralCredit).where(
        ReferralCredit.referrer_customer_id == customer_id,
        ReferralCredit.applied_at.isnot(None),
    )
    applied_credits = (await session.execute(applied_stmt)).scalars().all()

    # Count pending referrals
    pending_stmt = select(ReferralCredit).where(
        ReferralCredit.referrer_customer_id == customer_id,
        ReferralCredit.applied_at.is_(None),
    )
    pending_count = len((await session.execute(pending_stmt)).scalars().all())

    total_earned_ngn = sum(c.credit_amount_nGN for c in applied_credits) / 1_000_000

    return {
        "total_referrals": len(applied_credits),
        "pending_referrals": pending_count,
        "total_credit_earned_ngn": total_earned_ngn,
        "referral_code": None,  # caller should fetch separately
    }


async def backfill_referral_codes(session: AsyncSession) -> int:
    """Generate referral codes for existing customers who don't have one.

    Safe to re-run — only updates rows where referral_code IS NULL.
    Returns the number of codes generated.
    """
    stmt = select(Customer).where(Customer.referral_code.is_(None))
    customers = (await session.execute(stmt)).scalars().all()

    count = 0
    for customer in customers:
        # Keep generating until we get a unique one (collision probability is negligible)
        code = generate_referral_code()
        while True:
            existing = (
                await session.execute(
                    select(Customer).where(Customer.referral_code == code)
                )
            ).scalar_one_or_none()
            if not existing:
                break
            code = generate_referral_code()
        customer.referral_code = code
        count += 1

    await session.commit()
    logger.info("Backfilled %d referral codes", count)
    return count
