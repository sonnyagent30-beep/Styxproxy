"""Customer resolution helpers.

Extracted from app/routers/payments.py so both /payments/initiate and
/orders/create can share the same "resolve-or-create Customer from
phone or email" semantics.

Decision (Dannion, Jul 28 19:30): account-per-email model — no fuzzy
matching, no merge logic. Each unique email becomes its own Customer row.
A returning email-only customer who forgets their original email silently
ends up with a second account (acceptable per product decision).
"""
import hashlib

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Customer, PlatformAccount


def placeholder_phone_from_email(email: str) -> str:
    """Build a stable placeholder phone for anonymous customers.

    Format: +anon<sha256[:12]>@styxproxy.local. Two different emails
    yield two different phones so the customers.phone UNIQUE constraint
    isn't violated when the same device browses as multiple anonymous
    customers.

    Real customers will replace this with their actual phone via the
    trial flow or future profile update.
    """
    digest = hashlib.sha256(email.encode("utf-8")).hexdigest()[:12]
    return f"+anon{digest}@styxproxy.local"


async def get_or_create_customer(
    session: AsyncSession,
    *,
    phone: str | None,
    email: str | None,
    platform_account: PlatformAccount | None,
) -> Customer | None:
    """Find or create the Customer row for this checkout attempt.

    Resolution order:
    1. If we have a phone, look up by phone (UNIQUE). If found, set
       customer_id on the platform_account (if anonymous) and return it.
    2. If we have an email but no phone (or phone didn't match), look up
       by phone-placeholder derived from the email hash. Existing ones
       come back.
    3. Otherwise create a new Customer row with the placeholder phone
       and the supplied email, then link it to the platform_account.

    Returns None only when both phone and email are missing.
    """
    if not phone and not email:
        return None

    if phone:
        existing = (
            await session.execute(select(Customer).where(Customer.phone == phone))
        ).scalar_one_or_none()
        if existing:
            if platform_account and platform_account.customer_id is None:
                platform_account.customer_id = existing.id
                await session.commit()
            return existing

    if not email:
        return None
    placeholder = placeholder_phone_from_email(email)
    existing = (
        await session.execute(select(Customer).where(Customer.phone == placeholder))
    ).scalar_one_or_none()
    if existing:
        if platform_account and platform_account.customer_id is None:
            platform_account.customer_id = existing.id
            await session.commit()
        return existing

    name = email.split("@")[0][:100] or "Customer"
    customer = Customer(
        phone=placeholder,
        name=name,
        blocked=False,
        free_trials_used_today=0,
    )
    session.add(customer)
    await session.flush()
    if platform_account:
        platform_account.customer_id = customer.id
    await session.commit()
    await session.refresh(customer)
    return customer
