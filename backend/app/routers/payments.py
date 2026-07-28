"""Payments router."""

import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_account
from app.database import get_session
from app.models import Customer, PlatformAccount
from app.schemas import PaymentInitiateRequest, PaymentInitiateResponse, PaymentStatusResponse
from app.services.audit import log_audit_event
from app.services.flutterwave import create_flutterwave_invoice, verify_flutterwave_payment

router = APIRouter(prefix="/api/payments", tags=["payments"])

PRODUCT_PRICES = {
    "ISP-NG-1": 5000,
    "ISP-NG-2": 9500,
    "DC-NG-1": 8000,
    "RESIDENTIAL-UK-1": 12000,
    "RESIDENTIAL-US-1": 10000,
    "MOBILE-DE-1": 15000,
    "MOBILE-JP-1": 18000,
}


def _placeholder_phone_from_email(email: str) -> str:
    """Build a stable placeholder phone for anonymous customers using email local part.

    Format: +anon-<email-hash-prefix>@styxproxy.local. We use a hashed form
    so two different emails yield two different "phones" (preserving
    uniqueness against the customers.phone UNIQUE constraint). Real
    customers will replace this with their actual phone via the trial
    flow or future profile update.
    """
    import hashlib
    digest = hashlib.sha256(email.encode("utf-8")).hexdigest()[:12]
    return f"+anon{digest}@styxproxy.local"


async def _get_or_create_customer(
    session: AsyncSession,
    *,
    phone: str | None,
    email: str | None,
    platform_account: PlatformAccount | None,
) -> Customer | None:
    """Find or create the Customer row tied to this checkout attempt.

    Resolution order:
    1. If we have a phone, look it up by phone (UNIQUE). If found, set
       customer_id on the platform_account (if any) and return it.
    2. If we have an email but no phone, look up by phone-placeholder
       derived from the email hash. (Existing ones come back.)
    3. Otherwise create a Customer row with the placeholder phone and the
       supplied email, then link it to the platform_account if any.
    """
    if not phone and not email:
        return None

    if phone:
        existing = (await session.execute(select(Customer).where(Customer.phone == phone))).scalar_one_or_none()
        if existing:
            if platform_account and platform_account.customer_id is None:
                platform_account.customer_id = existing.id
                await session.commit()
            return existing

    # No phone or phone didn't match — derive a placeholder from email
    if not email:
        return None
    placeholder = _placeholder_phone_from_email(email)
    existing = (
        await session.execute(select(Customer).where(Customer.phone == placeholder))
    ).scalar_one_or_none()
    if existing:
        if platform_account and platform_account.customer_id is None:
            platform_account.customer_id = existing.id
            await session.commit()
        return existing

    # Create new
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


@router.post("/initiate", response_model=PaymentInitiateResponse, status_code=status.HTTP_201_CREATED)
async def initiate_payment(
    request: PaymentInitiateRequest,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_account),
):
    """Initiate payment — supports anonymous checkout.

    Previously, this endpoint required a Customer row (current_user.customer)
    and rejected with HTTP 400 if missing. That blocked all first-time
    customers from checking out via /order/checkout (no Customer until
    /api/session/init has been called AND a phone has been linked).

    Now: if the caller (FE) supplies customer_email and/or customer_phone in
    the body, we get-or-create a Customer row tied to the request and to
    the current PlatformAccount (so subsequent calls — orders/create,
    trial/claim — see the same customer).
    """
    price = PRODUCT_PRICES.get(request.plan_code)
    if not price:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid plan code")
    if not request.customer_email and not request.customer_phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either customer_email or customer_phone is required",
        )

    # Resolve the customer from the request body (allow anonymous before
    # get_current_account would have produced one).
    platform_account = current_user.get("platform_account") if isinstance(current_user, dict) else None
    customer = await _get_or_create_customer(
        session,
        phone=request.customer_phone,
        email=request.customer_email,
        platform_account=platform_account,
    )
    if customer is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to resolve or create customer",
        )

    total_amount = price * request.quantity
    # When the caller has a real phone we use it; otherwise the customer's
    # placeholder phone goes to Flutterwave for the fraud check.
    fw_phone = customer.phone
    fw_email = request.customer_email or f"{customer.phone}@styxproxy.com"

    try:
        result = await create_flutterwave_invoice(
            amount=total_amount,
            customer_email=fw_email,
            customer_phone=fw_phone,
            currency="NGN",
            callback_url=request.callback_url,
            description=f"Payment for {request.plan_code}",
        )
    except Exception as e:
        await log_audit_event(
            session,
            event_type="payment_initiate_failed",
            phone=customer.phone,
            details={"plan_code": request.plan_code, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to initiate payment: {str(e)}"
        )

    payment_id = str(uuid.uuid4())
    await log_audit_event(
        session,
        event_type="payment_initiated",
        phone=customer.phone,
        details={
            "plan_code": request.plan_code,
            "quantity": request.quantity,
            "amount_ngn": total_amount,
            "anonymous": platform_account is None or platform_account.customer_id == customer.id,
        },
    )

    return PaymentInitiateResponse(
        payment_id=payment_id,
        checkout_url=result.get("checkout_url", ""),
        amount_ngn=total_amount,
        expires_at=datetime.utcnow() + timedelta(minutes=30),
    )


@router.get("/{tx_ref}/status", response_model=PaymentStatusResponse)
async def get_payment_status(
    tx_ref: str, session: AsyncSession = Depends(get_session), current_user: dict = Depends(get_current_account)
):
    customer = current_user["customer"]
    if not customer:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No customer profile found")
    try:
        payment_data = await verify_flutterwave_payment(tx_ref)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to verify payment: {str(e)}"
        )
    return PaymentStatusResponse(
        tx_ref=tx_ref,
        status=payment_data.get("status", "unknown"),
        amount=payment_data.get("amount", 0),
        currency=payment_data.get("currency", "NGN"),
    )
