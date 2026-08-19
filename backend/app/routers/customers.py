"""Customer self-service GDPR router."""

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_account
from app.database import get_session
from app.models import (
    ConsentEvent,
    Customer,
    FreeTrial,
    Order,
    StyxproxyCredential,
)
from app.schemas import ReferralCodeResponse
from app.services.referral import get_referral_stats_for_customer

router = APIRouter(prefix="/api", tags=["customers"])


# ─── Auth dependency ──────────────────────────────────────────────────────────

async def get_current_customer(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """Return the Customer for the authenticated caller.

    Uses the same JWT/device pattern as orders.py — get_current_account.
    Raises 401 if the caller has no valid JWT or no linked customer.
    """
    auth_data = await get_current_account(request)
    customer = auth_data.get("customer")
    if customer is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated as a customer",
        )
    return customer


# ─── Pydantic schemas ─────────────────────────────────────────────────────────

ConsentRequest = BaseModel
ConsentResponse = BaseModel


class CustomerProfile(BaseModel):
    phone: str
    name: str
    email: Optional[str] = None  # derived from orders
    created_at: datetime
    order_count: int
    lifetime_value_ngn: float


class OrderSummary(BaseModel):
    order_id: str
    status: str
    plan_code: Optional[str]
    country: Optional[str]
    created_at: datetime
    amount_paid_ngn: float


class CredentialSummary(BaseModel):
    id: int
    styxproxy_username: str
    upstream_proxy_ip: Optional[str]
    upstream_proxy_port: Optional[int]
    expires_at: Optional[datetime]
    status: str


class TrialSummary(BaseModel):
    id: int
    trial_date: datetime
    status: Optional[str]
    reward_usd: Optional[float]


class DataExport(BaseModel):
    customer: dict
    orders: list[dict]
    credentials: list[dict]
    trials: list[dict]


class AnonymizeResponse(BaseModel):
    status: str
    retained_records: str


class ConsentRequestSchema(BaseModel):
    consent_type: str
    version: str
    granted: bool


# ─── Endpoints ────────────────────────────────────────────────────────────────


@router.get("/me", response_model=CustomerProfile)
async def get_me(
    customer: Customer = Depends(get_current_customer),
    session: AsyncSession = Depends(get_session),
):
    """Return the current customer's profile."""
    # Count orders
    orders_result = await session.execute(
        select(Order).where(Order.customer_id == customer.id)
    )
    orders = orders_result.scalars().all()

    # Derive email from orders if available
    email = None
    for order in orders:
        if order.customer_email:
            email = order.customer_email
            break

    return CustomerProfile(
        phone=customer.phone,
        name=customer.name,
        email=email,
        created_at=customer.created_at,
        order_count=len(orders),
        lifetime_value_ngn=float(customer.lifetime_value_ngn or 0),
    )


@router.get("/me/data-export", response_model=DataExport)
async def data_export(
    customer: Customer = Depends(get_current_customer),
    session: AsyncSession = Depends(get_session),
):
    """GDPR data export — all data held about the authenticated customer."""
    # Customer data
    customer_data = {
        "phone": customer.phone,
        "name": customer.name,
        "created_at": customer.created_at.isoformat() if customer.created_at else None,
        "consent_given": customer.consent_given,
        "consent_version": customer.consent_version,
    }

    # Orders
    orders_result = await session.execute(
        select(Order).where(Order.customer_id == customer.id)
    )
    orders = orders_result.scalars().all()
    orders_data = [
        {
            "order_id": o.id,
            "status": o.status,
            "plan_code": o.plan_code,
            "country": o.country,
            "created_at": o.created_at.isoformat() if o.created_at else None,
            "amount_paid_ngn": float(o.amount_paid_ngn or 0),
        }
        for o in orders
    ]

    # Credentials
    creds_result = await session.execute(
        select(StyxproxyCredential).where(StyxproxyCredential.customer_id == customer.id)
    )
    creds = creds_result.scalars().all()
    creds_data = [
        {
            "id": c.id,
            "styxproxy_username": c.styxproxy_username,
            "upstream_proxy_ip": c.upstream_proxy_ip,
            "upstream_proxy_port": c.upstream_proxy_port,
            "expires_at": c.expires_at.isoformat() if c.expires_at else None,
            "status": c.status,
        }
        for c in creds
    ]

    # Trials
    trials_result = await session.execute(
        select(FreeTrial).where(FreeTrial.phone == customer.phone)
    )
    trials = trials_result.scalars().all()
    trials_data = [
        {
            "id": t.id,
            "trial_date": t.trial_date.isoformat() if t.trial_date else None,
            "status": t.status,
            "reward_usd": float(t.reward_usd or 0) if t.reward_usd else None,
        }
        for t in trials
    ]

    return DataExport(
        customer=customer_data,
        orders=orders_data,
        credentials=creds_data,
        trials=trials_data,
    )


@router.delete("/me", response_model=AnonymizeResponse)
async def delete_me(
    request: Request,
    customer: Customer = Depends(get_current_customer),
    session: AsyncSession = Depends(get_session),
):
    """GDPR right to be forgotten — anonymize the customer record.

    Retains orders for accounting compliance but unlinks the customer.
    Clears phone, name, and consent fields.
    """
    anon_id = f"DELETED_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)

    # Anonymize customer record
    await session.execute(
        update(Customer)
        .where(Customer.id == customer.id)
        .values(
            phone=anon_id,
            name="Deleted User",
            consent_given=False,
            consent_version=None,
            consent_at=None,
        )
    )

    # Unlink customer from orders (retain order records for tax compliance)
    await session.execute(
        update(Order)
        .where(Order.customer_id == customer.id)
        .values(customer_id=None)
    )

    await session.commit()

    return AnonymizeResponse(
        status="anonymized",
        retained_records="orders for tax compliance",
    )


@router.post("/consent", response_model=dict)
async def record_consent(
    consent_req: ConsentRequestSchema,
    request: Request,
    customer: Customer = Depends(get_current_customer),
    session: AsyncSession = Depends(get_session),
):
    """Record a consent event and update the customer's consent fields.

    Also stores an immutable audit record in consent_events.
    """
    now = datetime.now(timezone.utc)

    # Update customer consent fields
    await session.execute(
        update(Customer)
        .where(Customer.id == customer.id)
        .values(
            consent_given=consent_req.granted,
            consent_version=consent_req.version,
            consent_at=now,
        )
    )

    # Insert immutable consent event
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    if request.client:
        ip_address = request.client.host
    user_agent = request.headers.get("user-agent")

    consent_event = ConsentEvent(
        customer_id=customer.id,
        consent_type=consent_req.consent_type,
        consent_version=consent_req.version,
        granted=consent_req.granted,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    session.add(consent_event)

    await session.commit()

    return {"status": "recorded"}


@router.get("/me/referral-code", response_model=ReferralCodeResponse)
async def get_my_referral_code(
    customer: Customer = Depends(get_current_customer),
    session: AsyncSession = Depends(get_session),
):
    """Return the current customer's referral code and stats.

    If the customer doesn't have a referral_code yet (pre-migration accounts),
    one is generated on-demand.
    """
    from app.services.referral import backfill_referral_codes, generate_referral_code

    if not customer.referral_code:
        # Generate a code for this pre-migration account
        customer.referral_code = generate_referral_code()
        await session.commit()

    stats = await get_referral_stats_for_customer(session, customer_id=customer.id)
    return ReferralCodeResponse(
        referral_code=customer.referral_code,
        total_referrals=stats["total_referrals"],
        pending_referrals=stats["pending_referrals"],
        total_credit_earned_ngn=stats["total_credit_earned_ngn"],
    )
