"""Orders router."""
from datetime import datetime, timedelta
import random
import string

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
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
    device_id = current_user.get("device_id")
    if not customer:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No customer profile found")
    price = PRODUCT_PRICES.get(request.plan_code)
    if not price:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid plan code")
    total_amount = price * request.quantity

    # In-flight payment check: prevent double payments on the same device
    # If there's a 'pending' order for this device in the last 5 minutes, block
    if device_id:
        cutoff = datetime.utcnow() - timedelta(minutes=5)
        inflight_stmt = select(Order).where(
            Order.platform_account_id == platform_account.id,
            Order.status == "pending",
            Order.created_at >= cutoff,
        )
        inflight = (await session.execute(inflight_stmt)).scalars().first()
        if inflight is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Payment already in progress for order {inflight.order_id}. Complete or cancel it before starting a new one.",
            )

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
            cred_brief = BuncheCredentialBrief(id=cred.id, bun_username=cred.bun_username, protocol=cred.protocol or 'socks5', upstream_proxy_ip=cred.upstream_proxy_ip, upstream_proxy_port=cred.upstream_proxy_port, status=cred.status)
    return OrderResponse(order_id=order.order_id, status=order.status, plan_type=order.plan_type, country=order.country, amount_paid_ngn=order.amount_paid_ngn, bunche_credential=cred_brief, created_at=order.created_at, expires_at=order.expires_at)


@router.get("/by-device", response_model=list[OrderResponse])
async def list_orders_by_device(
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_account),
):
    """List all orders for the current device/platform account.

    Lets anonymous web customers see their past orders without login.
    Sorted by created_at DESC (newest first).
    """
    platform_account = current_user["platform_account"]
    stmt = (
        select(Order)
        .where(Order.platform_account_id == platform_account.id)
        .order_by(Order.created_at.desc())
        .limit(50)
    )
    orders = (await session.execute(stmt)).scalars().all()

    # Build brief responses
    results = []
    for order in orders:
        cred_brief = None
        if order.bunche_credential_id:
            cred_stmt = select(BuncheCredential).where(BuncheCredential.id == order.bunche_credential_id)
            cred = (await session.execute(cred_stmt)).scalar_one_or_none()
            if cred:
                cred_brief = BuncheCredentialBrief(
                    id=cred.id,
                    bun_username=cred.bun_username,
                    protocol=cred.protocol or 'socks5',
                    upstream_proxy_ip=cred.upstream_proxy_ip,
                    upstream_proxy_port=cred.upstream_proxy_port,
                    status=cred.status,
                )
        customer = current_user.get("customer")
        results.append(OrderResponse(
            order_id=order.order_id,
            status=order.status,
            plan_type=order.plan_type,
            country=order.country,
            amount_paid_ngn=order.amount_paid_ngn,
            bunche_credential=cred_brief,
            created_at=order.created_at,
            expires_at=order.expires_at,
            customer_name=customer.name if customer and customer.name else None,
        ))
    return results


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
    rotation_count = 0
    max_rotations = 3
    if order.bunche_credential_id:
        cred_stmt = select(BuncheCredential).where(BuncheCredential.id == order.bunche_credential_id)
        cred_result = await session.execute(cred_stmt)
        cred = cred_result.scalar_one_or_none()
        if cred:
            rotation_count = getattr(cred, 'rotation_count', 0) or 0
            max_rotations = getattr(cred, 'max_rotations', 3) or 3
            cred_brief = BuncheCredentialBrief(id=cred.id, bun_username=cred.bun_username, protocol=cred.protocol or 'socks5', upstream_proxy_ip=cred.upstream_proxy_ip, upstream_proxy_port=cred.upstream_proxy_port, status=cred.status)
    is_renewable = order.status == 'active' and order.expires_at is not None
    return OrderResponse(
        order_id=order.order_id,
        status=order.status,
        plan_type=order.plan_type,
        country=order.country,
        amount_paid_ngn=order.amount_paid_ngn,
        bunche_credential=cred_brief,
        created_at=order.created_at,
        expires_at=order.expires_at,
        customer_name=customer.name if customer and customer.name else None,
        is_renewable=is_renewable,
        rotation_count=rotation_count,
        max_rotations=max_rotations,
    )

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


class RotateResponse(BaseModel):
    order_id: str
    bunche_credential: BuncheCredentialBrief
    rotation_count: int
    max_rotations: int

    model_config = {"from_attributes": True}


@router.post("/{order_id}/rotate", response_model=RotateResponse)
async def rotate_proxy(order_id: str, session: AsyncSession = Depends(get_session), current_user: dict = Depends(get_current_account)):
    """Rotate the upstream proxy IP for this credential.

    Frontend or backend is responsible for:
    - Hitting the provider API to get a new IP
    - Updating the credential row with new IP/port

    For this lightweight implementation:
    - Generate a random placeholder IP (192.0.2.X — TEST-NET-1 reserved range, safe)
      and increment rotation_count
    - Real production: integrate with Proxy-Seller / DataImpulse rotation API

    Max 3 rotations per credential; reject the 4th.
    """
    MAX_ROTATIONS = 3
    customer = current_user["customer"]
    if not customer:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No customer profile found")
    stmt = select(Order).where(Order.order_id == order_id, Order.customer_phone == customer.phone)
    result = await session.execute(stmt)
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    if not order.bunche_credential_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No credential to rotate")
    cred_stmt = select(BuncheCredential).where(BuncheCredential.id == order.bunche_credential_id)
    cred_result = await session.execute(cred_stmt)
    cred = cred_result.scalar_one_or_none()
    if not cred:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Credential not found")
    current_count = getattr(cred, 'rotation_count', 0) or 0
    if current_count >= MAX_ROTATIONS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Rotation limit reached ({MAX_ROTATIONS} per proxy)")
    # Bump count and assign a placeholder rotated IP
    setattr(cred, 'rotation_count', current_count + 1)
    # Generate a placeholder rotated IP in TEST-NET-1 (RFC 5737)
    new_ip_last_octet = random.randint(1, 254)
    cred.upstream_proxy_ip = f"192.0.2.{new_ip_last_octet}"
    await session.commit()
    await session.refresh(cred)
    await log_audit_event(session, event_type="proxy_rotated", phone=customer.phone, order_id=order_id, details={"rotation_count": current_count + 1, "new_ip": cred.upstream_proxy_ip})
    return RotateResponse(
        order_id=order_id,
        bunche_credential=BuncheCredentialBrief(
            id=cred.id,
            bun_username=cred.bun_username,
            protocol=cred.protocol or 'socks5',
            upstream_proxy_ip=cred.upstream_proxy_ip,
            upstream_proxy_port=cred.upstream_proxy_port,
            status=cred.status,
        ),
        rotation_count=getattr(cred, 'rotation_count', 0) or 0,
        max_rotations=MAX_ROTATIONS,
    )
