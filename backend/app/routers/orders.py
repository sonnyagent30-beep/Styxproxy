"""Orders router."""
from datetime import datetime
import random
import string

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_session
from app.models import Order, Customer, BuncheCredential
from app.schemas import (
    OrderCreateRequest,
    OrderResponse,
    OrderCancelRequest,
    OrderCancelResponse,
    OrderReportDeadRequest,
    OrderReportDeadResponse,
    BuncheCredentialBrief,
)
from app.auth import get_current_account
from app.services.credential import create_credential
from app.services.audit import log_audit_event

router = APIRouter(prefix="/api/orders", tags=["orders"])

PRODUCT_PRICES = {
    "ISP-NG-1": 5000, "ISP-NG-2": 9500, "DC-NG-1": 8000,
    "RESIDENTIAL-UK-1": 12000, "RESIDENTIAL-US-1": 10000,
    "MOBILE-DE-1": 15000, "MOBILE-JP-1": 18000,
}

def generate_order_id() -> str:
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"ORD-{suffix}"


@router.post("/create", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    request: OrderCreateRequest,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_account),
):
    customer = current_user["customer"]
    platform_account = current_user["platform_account"]
    if not customer:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No customer profile found")
    price = PRODUCT_PRICES.get(request.plan_code)
    if not price:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid plan code")
    total_amount = price * request.quantity
    order_id = generate_order_id()
    plan_type = request.plan_code.split("-")[0] if "-" in request.plan_code else "ISP"
    order = Order(
        order_id=order_id,
        platform_account_id=platform_account.id,
        customer_phone=customer.phone,
        plan_type=plan_type,
        plan_code=request.plan_code,
        country=request.country,
        quantity=request.quantity,
        amount_paid_ngn=total_amount,
        payment_reference=request.payment_reference,
        status="pending",
    )
    session.add(order)
    if request.payment_reference:
        order.status = "paid"
        credential = await create_credential(session, customer_phone=customer.phone, order_id=order_id, pool_type="paid", duration_days=30, country=request.country)
        order.bunche_credential_id = credential.id
        order.status = "active"
    await session.commit()
    await session.refresh(order)
    await log_audit_event(session, event_type="order_created", phone=customer.phone, order_id=order_id, details={"plan_code": request.plan_code, "country": request.country, "amount": total_amount, "status": order.status})
    cred_brief = None
    if order.bunche_credential_id:
        cred_stmt = select(BuncheCredential).where(BuncheCredential.id == order.bunche_credential_id)
        cred_result = await session.execute(cred_stmt)
        cred = cred_result.scalar_one_or_none()
        if cred:
            cred_brief = BuncheCredentialBrief(id=cred.id, bun_username=cred.bun_username, upstream_proxy_ip=cred.upstream_proxy_ip, upstream_proxy_port=cred.upstream_proxy_port, status=cred.status)
    return OrderResponse(order_id=order.order_id, status=order.status, plan_type=order.plan_type, country=order.country, amount_paid_ngn=order.amount_paid_ngn, bunche_credential=cred_brief, created_at=order.created_at, expires_at=order.expires_at)


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(order_id: str, session: AsyncSession = Depends(get_session), current_user: dict = Depends(get_current_account)):
    customer = current_user["customer"]
    if not customer:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No customer profile found")
    stmt = select(Order).where(Order.order_id == order_id, Order.customer_phone == customer.phone)
    result = await session.execute(stmt)
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    cred_brief = None
    if order.bunche_credential_id:
        cred_stmt = select(BuncheCredential).where(BuncheCredential.id == order.bunche_credential_id)
        cred_result = await session.execute(cred_stmt)
        cred = cred_result.scalar_one_or_none()
        if cred:
            cred_brief = BuncheCredentialBrief(id=cred.id, bun_username=cred.bun_username, upstream_proxy_ip=cred.upstream_proxy_ip, upstream_proxy_port=cred.upstream_proxy_port, status=cred.status)
    return OrderResponse(order_id=order.order_id, status=order.status, plan_type=order.plan_type, country=order.country, amount_paid_ngn=order.amount_paid_ngn, bunche_credential=cred_brief, created_at=order.created_at, expires_at=order.expires_at)

@router.post("/{order_id}/cancel", response_model=OrderCancelResponse)
async def cancel_order(order_id: str, request: OrderCancelRequest, session: AsyncSession = Depends(get_session), current_user: dict = Depends(get_current_account)):
    customer = current_user["customer"]
    if not customer:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No customer profile found")
    stmt = select(Order).where(Order.order_id == order_id, Order.customer_phone == customer.phone)
    result = await session.execute(stmt)
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    if order.status in ["cancelled", "refunded"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Order already cancelled or refunded")
    order.status = "cancelled"
    order.refund_requested = True
    order.refund_reason = request.reason
    if order.bunche_credential_id:
        cred_stmt = select(BuncheCredential).where(BuncheCredential.id == order.bunche_credential_id)
        cred_result = await session.execute(cred_stmt)
        cred = cred_result.scalar_one_or_none()
        if cred:
            cred.status = "revoked"
    await session.commit()
    await log_audit_event(session, event_type="order_cancelled", phone=customer.phone, order_id=order_id, details={"reason": request.reason})
    return OrderCancelResponse(order_id=order_id, status="cancelled", refund_processed=True, refund_amount_ngn=order.amount_paid_ngn)

@router.post("/{order_id}/report-dead", response_model=OrderReportDeadResponse)
async def report_dead_ip(order_id: str, request: OrderReportDeadRequest, session: AsyncSession = Depends(get_session), current_user: dict = Depends(get_current_account)):
    customer = current_user["customer"]
    if not customer:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No customer profile found")
    stmt = select(Order).where(Order.order_id == order_id, Order.customer_phone == customer.phone)
    result = await session.execute(stmt)
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    if order.status != "active":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Order is not active")
    order.ban_reported = True
    order.screenshot_url = request.screenshot_url
    order.status = "pending_verification"
    order.ban_verified = "pending"
    await session.commit()
    await log_audit_event(session, event_type="ip_ban_reported", phone=customer.phone, order_id=order_id, details={"screenshot_url": request.screenshot_url, "issue_description": request.issue_description})
    return OrderReportDeadResponse(order_id=order_id, ban_reported=True, status="pending_verification", replacement_estimate_hours=24)
