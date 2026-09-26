import asyncio
from uuid import uuid4
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import FeatureFlag, Order
from app.schemas import PaymentInitiateResponse
from app.routers.schemas import PaymentInitiateRequest
from app.services.customer import get_or_create_customer
from app.services.flutterwave import create_flutterwave_invoice

router = APIRouter(prefix="/api/payments", tags=["payments"])


@router.post("/initiate", response_model=PaymentInitiateResponse, status_code=status.HTTP_201_CREATED)
async def initiate_payment(
    request: PaymentInitiateRequest,
    session: AsyncSession = Depends(get_session),
):
    kill_switch = (
        await session.execute(select(FeatureFlag).where(FeatureFlag.name == "checkout_disabled"))
    ).scalar_one_or_none()
    if kill_switch and kill_switch.enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Checkout is temporarily disabled.",
        )

    from app.routers.orders import resolve_plan, generate_order_id
    plan = await resolve_plan(session, request.plan_code)
    if not plan:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid plan code")
    price = float(plan.price_per_gb if plan.price_per_gb is not None else plan.price_ngn)
    total_amount = price * request.quantity

    customer = await get_or_create_customer(
        session,
        phone=None,
        email=request.customer_email,
        platform_account=None,
    )
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No customer profile found.",
        )

    # Use frontend payment_reference if provided (STX- format), otherwise generate our own
    tx_ref = request.payment_reference or f"TXF-{uuid4().hex[:8].upper()}"

    result = await create_flutterwave_invoice(
        amount=total_amount,
        customer_email=request.customer_email or "",
        customer_phone=customer.phone,
        currency="NGN",
        tx_ref=tx_ref,  # Pass our tx_ref to flutterwave
        callback_url="https://styxproxy.com/thank-you?tx_ref=" + tx_ref,
        description=f"Payment for {request.plan_code}",
    )

    order_id = generate_order_id()

    order = Order(
        order_id=order_id,
        platform_account_id=None,
        customer_phone=customer.phone,
        plan_type=plan.plan_type.lower(),
        plan_code=request.plan_code,
        country=plan.country,
        quantity=request.quantity,
        amount_paid_ngn=total_amount,
        payment_reference=tx_ref,
        status="pending",
    )
    session.add(order)
    await session.commit()

    return PaymentInitiateResponse(
        payment_id=str(uuid4()),
        checkout_url=result.get("checkout_url", ""),
        amount_ngn=total_amount,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
    )

# ============== Gateways ==============

@router.get("/gateways")
async def list_gateways(session: AsyncSession = Depends(get_session)):
    """List available payment gateways with their status."""
    flags = {}
    for name in ("flutterwave_enabled", "paystack_enabled", "stripe_enabled", "paynow_enabled"):
        flag = (
            await session.execute(select(FeatureFlag).where(FeatureFlag.name == name))
        ).scalar_one_or_none()
        flags[name] = bool(flag and flag.enabled)
    
    return {
        "gateways": {
            "flutterwave": {
                "available": flags["flutterwave_enabled"],
                "label": "Flutterwave",
                "icon": "💳",
                "description": "Card, Bank Transfer, USSD, QR"
            },
            "paystack": {
                "available": flags["paystack_enabled"],
                "label": "Paystack",
                "icon": "🏦",
                "description": "Card, Bank Transfer, USSD"
            },
            "stripe": {
                "available": flags["stripe_enabled"],
                "label": "Stripe",
                "icon": "💰",
                "description": "International cards"
            },
            "paynow": {
                "available": flags["paynow_enabled"],
                "label": "Paynow",
                "icon": "₿",
                "description": "Bitcoin, USDT, Crypto"
            }
        }
    }
