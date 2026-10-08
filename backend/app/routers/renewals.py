"""Renewals router — proxy subscription renewal endpoints.

POST /api/renewals/initiate  — create renewal order + payment
GET  /api/renewals/order/{order_id} — list renewals for an order
GET  /api/renewals/{renewal_id} — get single renewal
POST /api/renewals/{renewal_id}/complete — complete a pending renewal (worker/internal)
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_account
from app.database import get_session
from app.limiter import limiter
from app.models import Order, Renewal
from app.schemas import (
    RenewalCreateRequest,
    RenewalHistoryResponse,
    RenewalInitiateResponse,
    RenewalResponse,
)
from app.services.renewal_service import (
    complete_renewal,
    create_renewal_order,
    get_renewals_for_order,
)
from app.services.flutterwave import create_flutterwave_invoice
from app.services.paystack import create_paystack_transaction
from app.services.customer import get_or_create_customer, placeholder_email_from_device

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/renewals", tags=["renewals"])

ORDER_TTL_MINUTES = 30


@router.post("/initiate", response_model=RenewalInitiateResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def initiate_renewal(
    request: Request,
    body: RenewalCreateRequest,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_account),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
):
    """Initiate a renewal payment for an existing order.

    For residential/mobile: customer selects GB amount (tiers + custom, 5 GB min).
    For DC/ISP: no GB selection, just extends expiry by 30 days.
    """
    # ── Resolve the original order ──
    order = (
        await session.execute(select(Order).where(Order.order_id == body.order_id))
    ).scalar_one_or_none()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Verify ownership
    customer = current_user.get("customer")
    platform_account = current_user.get("platform_account")

    if customer and order.customer_phone and order.customer_phone != customer.phone:
        raise HTTPException(status_code=403, detail="Order does not belong to this customer")

    if platform_account and order.platform_account_id and order.platform_account_id != platform_account.id:
        raise HTTPException(status_code=403, detail="Order does not belong to this account")

    # ── Determine plan type and pricing ──
    plan_type = (order.plan_type or "").lower()

    if plan_type in ("residential", "mobile"):
        # Per-GB pricing
        if not body.quantity_gb or body.quantity_gb < 5:
            raise HTTPException(status_code=400, detail="Minimum renewal is 5 GB")

        # Resolve price from the plan
        from app.routers.orders import resolve_plan
        plan = await resolve_plan(session, order.plan_code or "", country=order.country)
        if not plan:
            raise HTTPException(status_code=400, detail="Cannot resolve plan for pricing")

        price_per_gb = float(plan.price_per_gb or 0)
        if price_per_gb <= 0:
            raise HTTPException(status_code=400, detail="Plan has no per-GB pricing configured")

        total_amount = price_per_gb * body.quantity_gb
    else:
        # DC/ISP: per-IP pricing (quantity=1)
        from app.routers.orders import resolve_plan
        plan = await resolve_plan(session, order.plan_code or "", country=order.country)
        if not plan:
            raise HTTPException(status_code=400, detail="Cannot resolve plan for pricing")

        total_amount = float(plan.price_ngn or 0)
        if total_amount <= 0:
            raise HTTPException(status_code=400, detail="Plan has no pricing configured")

    # ── Idempotency check ──
    if idempotency_key:
        existing = (
            await session.execute(
                select(Renewal).where(Renewal.payment_reference == idempotency_key)
            )
        ).scalars().first()
        if existing:
            return RenewalInitiateResponse(
                renewal_id=existing.id,
                order_id=existing.order_id,
                checkout_url="",
                amount_ngn=float(existing.amount_paid_ngn),
                currency="NGN",
                expires_at=existing.created_at + timedelta(minutes=ORDER_TTL_MINUTES),
                tx_ref=existing.tx_ref or "",
            )

    # ── Create renewal record ──
    renewal = await create_renewal_order(
        session=session,
        order_id=body.order_id,
        quantity_gb=body.quantity_gb if plan_type in ("residential", "mobile") else None,
        amount_paid_ngn=total_amount,
        payment_reference=idempotency_key,
        tx_ref=None,
    )

    # ── Create payment ──
    tx_ref = f"TXF-{uuid.uuid4().hex[:12].upper()}"
    renewal.tx_ref = tx_ref
    renewal.payment_reference = tx_ref
    await session.commit()

    callback_url = f"https://styxproxy.com/thank-you?order_id={body.order_id}&renewal_id={renewal.id}"

    gateway_email = body.customer_email or order.customer_email or ""
    if not gateway_email:
        device_id = current_user.get("device_id") or ""
        gateway_email = placeholder_email_from_device(device_id)

    try:
        if body.gateway == "paystack":
            result = await create_paystack_transaction(
                amount_ngn=total_amount,
                customer_email=gateway_email,
                customer_phone=order.customer_phone or "",
                callback_url=callback_url,
                description=f"Renewal for {body.order_id}",
                tx_ref=tx_ref,
            )
        else:
            result = await create_flutterwave_invoice(
                amount=total_amount,
                customer_email=gateway_email,
                customer_phone=order.customer_phone,
                currency="NGN",
                tx_ref=tx_ref,
                callback_url=callback_url,
                description=f"Renewal for {body.order_id}",
            )
    except Exception as e:
        logger.error("Renewal payment creation failed: %s", e)
        renewal.status = "failed"
        await session.commit()
        raise HTTPException(status_code=502, detail=f"Payment gateway error: {str(e)}")

    checkout_url = result.get("checkout_url", "")
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=ORDER_TTL_MINUTES)

    return RenewalInitiateResponse(
        renewal_id=renewal.id,
        order_id=body.order_id,
        checkout_url=checkout_url,
        amount_ngn=total_amount,
        currency="NGN",
        expires_at=expires_at,
        tx_ref=tx_ref,
    )


@router.get("/order/{order_id}", response_model=RenewalHistoryResponse)
async def list_order_renewals(
    order_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_account),
):
    """List all renewals for an order."""
    order = (
        await session.execute(select(Order).where(Order.order_id == order_id))
    ).scalar_one_or_none()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Verify ownership
    customer = current_user.get("customer")
    if customer and order.customer_phone and order.customer_phone != customer.phone:
        raise HTTPException(status_code=403, detail="Order does not belong to this customer")

    renewals = await get_renewals_for_order(session, order_id)
    return RenewalHistoryResponse(
        renewals=[RenewalResponse.model_validate(r) for r in renewals],
        total=len(renewals),
    )


@router.get("/{renewal_id}", response_model=RenewalResponse)
async def get_renewal(
    renewal_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_account),
):
    """Get a single renewal by ID."""
    renewal = (
        await session.execute(select(Renewal).where(Renewal.id == renewal_id))
    ).scalar_one_or_none()

    if not renewal:
        raise HTTPException(status_code=404, detail="Renewal not found")

    # Verify ownership via the parent order
    order = (
        await session.execute(select(Order).where(Order.order_id == renewal.order_id))
    ).scalar_one_or_none()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    customer = current_user.get("customer")
    if customer and order.customer_phone and order.customer_phone != customer.phone:
        raise HTTPException(status_code=403, detail="Order does not belong to this customer")

    return RenewalResponse.model_validate(renewal)


@router.post("/{renewal_id}/complete", response_model=RenewalResponse)
async def complete_renewal_endpoint(
    renewal_id: int,
    session: AsyncSession = Depends(get_session),
):
    """Complete a pending renewal — called by the fulfillment worker after payment webhook.

    This endpoint is internal (no auth) — it is called by the RQ worker, not the frontend.
    The worker is the only caller that knows payment has been confirmed.
    """
    renewal = await complete_renewal(session, renewal_id)
    if not renewal:
        raise HTTPException(status_code=404, detail="Renewal not found or already completed")
    return RenewalResponse.model_validate(renewal)
