"""Payments router — Payment Flow Rewrite (Sprint 025).

Key changes:
- Idempotency key support (Idempotency-Key header)
- Backend-owned tx_ref generation (frontend never sends payment_reference)
- Structured logging at every step
- Order expiry (30 min TTL)
- No silent except:pass — every failure is logged
"""
import logging
import re
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import FeatureFlag, Order
from app.schemas import PaymentInitiateResponse
from app.routers.schemas import PaymentInitiateRequest
from app.services.customer import get_or_create_customer
from app.services.flutterwave import create_flutterwave_invoice
from app.services.paystack import create_paystack_transaction

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/payments", tags=["payments"])

# Order TTL — pending orders expire after 30 minutes
ORDER_TTL_MINUTES = 30


@router.post("/initiate", response_model=PaymentInitiateResponse, status_code=status.HTTP_201_CREATED)
async def initiate_payment(
    request: PaymentInitiateRequest,
    session: AsyncSession = Depends(get_session),
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
):
    """Initiate a payment — create order and return gateway checkout URL.

    Idempotency: if Idempotency-Key header is provided and an order with
    that key already exists, return the original order instead of creating
    a duplicate. On failure, attempt to delete any partial order with that
    key so the client can retry safely.
    """
    log_ctx = {"idempotency_key": idempotency_key, "plan_code": request.plan_code, "gateway": request.gateway}

    # ── Kill switch ───────────────────────────────────────────────────────
    kill_switch = (
        await session.execute(select(FeatureFlag).where(FeatureFlag.name == "checkout_disabled"))
    ).scalar_one_or_none()
    if kill_switch and kill_switch.enabled:
        logger.warning("checkout disabled by feature flag", extra=log_ctx)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Checkout is temporarily disabled.",
        )

    # ── Idempotency check ────────────────────────────────────────────────
    if idempotency_key:
        existing = (
            await session.execute(
                select(Order).where(Order.idempotency_key == idempotency_key)
            )
        ).scalars().first()
        if existing:
            logger.info(
                "idempotent replay — returning existing order",
                extra={**log_ctx, "order_id": existing.order_id},
            )
            return PaymentInitiateResponse(
                payment_id=str(uuid.uuid4()),
                order_id=existing.order_id,
                checkout_url="",
                amount_ngn=float(existing.amount_paid_ngn or 0),
                expires_at=existing.expires_at or datetime.now(timezone.utc) + timedelta(minutes=ORDER_TTL_MINUTES),
            )

    # ── Resolve plan ─────────────────────────────────────────────────────
    from app.routers.orders import resolve_plan, generate_order_id

    plan = await resolve_plan(session, request.plan_code)
    if not plan:
        logger.warning("invalid plan code", extra=log_ctx)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid plan code")

    price = float(plan.price_per_gb if plan.price_per_gb is not None else plan.price_ngn)

    # Parse quantity from plan code suffix (e.g., "MOBILE-GH-5IP" → 5)
    quantity = request.quantity
    if '-' in request.plan_code and request.plan_code.endswith('IP'):
        parts = request.plan_code.rsplit('-', 2)
        if len(parts) >= 3:
            match = re.match(r'^(\d+)IP$', parts[2])
            if match:
                suffix_qty = int(match.group(1))
                if suffix_qty > 0:
                    quantity = suffix_qty

    total_amount = price * quantity

    # ── Get or create customer ───────────────────────────────────────────
    customer = await get_or_create_customer(
        session,
        phone=None,
        email=request.customer_email,
        platform_account=None,
    )
    if not customer:
        logger.warning("no customer profile", extra=log_ctx)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No customer profile found.",
        )

    # ── Backend-owned tx_ref ─────────────────────────────────────────────
    tx_ref = f"TXF-{uuid.uuid4().hex[:12].upper()}"

    # ── Generate order_id ────────────────────────────────────────────────
    order_id = generate_order_id()

    callback_url = f"https://styxproxy.com/thank-you?order_id={order_id}"

    # ── Create gateway transaction ───────────────────────────────────────
    try:
        if request.gateway == "paystack":
            result = await create_paystack_transaction(
                amount_ngn=total_amount,
                customer_email=request.customer_email or "",
                customer_phone=customer.phone or "",
                callback_url=callback_url,
                description=f"Payment for {request.plan_code}",
            )
        else:
            result = await create_flutterwave_invoice(
                amount=total_amount,
                customer_email=request.customer_email or "",
                customer_phone=customer.phone,
                currency="NGN",
                tx_ref=tx_ref,
                callback_url=callback_url,
                description=f"Payment for {request.plan_code}",
            )
    except Exception as e:
        logger.error(
            "gateway transaction creation failed",
            extra={**log_ctx, "error": str(e), "error_type": type(e).__name__},
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Payment gateway error: {str(e)}",
        )

    # ── Create order ─────────────────────────────────────────────────────
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=ORDER_TTL_MINUTES)
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
        tx_ref=tx_ref,
        status="pending",
        idempotency_key=idempotency_key,
        expires_at=expires_at,
    )
    session.add(order)

    try:
        await session.commit()
    except Exception as e:
        await session.rollback()
        # Idempotency failure path: attempt to delete partial order
        if idempotency_key:
            try:
                await session.execute(
                    Order.__table__.delete().where(Order.idempotency_key == idempotency_key)
                )
                await session.commit()
                logger.info(
                    "idempotency key released after failure",
                    extra={**log_ctx, "error": str(e)},
                )
            except Exception as delete_err:
                # Key stays locked — customer can generate a new key
                logger.error(
                    "idempotency key release failed — key stays locked",
                    extra={**log_ctx, "delete_error": str(delete_err)},
                )
        logger.error(
            "order creation failed",
            extra={**log_ctx, "error": str(e), "error_type": type(e).__name__},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create order. Please try again.",
        )

    logger.info(
        "payment initiated",
        extra={
            **log_ctx,
            "order_id": order_id,
            "tx_ref": tx_ref,
            "amount": total_amount,
            "customer_phone": customer.phone,
        },
    )

    return PaymentInitiateResponse(
        payment_id=str(uuid.uuid4()),
        order_id=order_id,
        checkout_url=result.get("checkout_url", ""),
        amount_ngn=total_amount,
        expires_at=expires_at,
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
                "description": "Card, Bank Transfer, USSD, QR",
            },
            "paystack": {
                "available": flags["paystack_enabled"],
                "label": "Paystack",
                "icon": "🏦",
                "description": "Card, Bank Transfer, USSD",
            },
            "stripe": {
                "available": flags["stripe_enabled"],
                "label": "Stripe",
                "icon": "💰",
                "description": "International cards",
            },
            "paynow": {
                "available": flags["paynow_enabled"],
                "label": "Paynow",
                "icon": "₿",
                "description": "Bitcoin, USDT, Crypto",
            },
        }
    }
