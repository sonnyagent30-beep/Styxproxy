"""Orders router."""

import random
import string
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

# Reportlab imports for PDF generation
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_account, get_password_hash
from app.database import get_session
from app.models import Customer, Order, StyxproxyCredential
from app.schemas import (
    OrderCancelRequest,
    OrderCancelResponse,
    OrderCreateRequest,
    OrderReportDeadRequest,
    OrderReportDeadResponse,
    OrderResponse,
    PrecheckRequest,
    PrecheckResponse,
    ReceiptOrderResponse,
    StyxproxyCredentialBrief,
)
from app.services.audit import log_audit_event
from app.services.credential import create_credential
from app.services.email import (
    send_credentials_rotated_email,
    send_new_order_notification,
    send_order_active_email,
    send_order_confirmation_email,
    send_refund_request_notification,
)
from app.services.logo_paths import get_logo_path
from app.services.provider import check_availability

router = APIRouter(prefix="/api/orders", tags=["orders"])

PRODUCT_PRICES = {
    "ISP-NG-1": 5000,
    "ISP-NG-2": 9500,
    "DC-NG-1": 8000,
    "RESIDENTIAL-UK-1": 12000,
    "RESIDENTIAL-US-1": 10000,
    "MOBILE-DE-1": 15000,
    "MOBILE-JP-1": 18000,
}

# Map plan codes to proxy types for provider API
PLAN_TYPE_MAP = {
    "ISP-NG-1": "isp",
    "ISP-NG-2": "isp",
    "DC-NG-1": "datacenter",
    "RESIDENTIAL-UK-1": "residential",
    "RESIDENTIAL-US-1": "residential",
    "MOBILE-DE-1": "mobile",
    "MOBILE-JP-1": "mobile",
}


@router.post("/precheck", response_model=PrecheckResponse)
async def precheck_order(
    request: PrecheckRequest,
):
    """Check if an order can be fulfilled - provider availability, pricing, delivery estimate."""
    # Validate plan code exists
    if request.plan_code not in PRODUCT_PRICES:
        return PrecheckResponse(
            available=False,
            reason="invalid_plan_code",
            estimated_delivery_seconds=0,
        )

    # Determine proxy type from plan code
    proxy_type = PLAN_TYPE_MAP.get(request.plan_code, "isp")

    # Country mapping for provider
    country_map = {"NG": "Nigeria", "UK": "United Kingdom", "US": "United States", "DE": "Germany", "JP": "Japan"}
    provider_country = country_map.get(request.country.upper(), request.country)

    # Call provider availability check
    result = await check_availability(
        plan_code=request.plan_code,
        country=provider_country,
        proxy_type=proxy_type,
        quantity=request.quantity,
    )

    return PrecheckResponse(
        available=result.available,
        reason=result.reason,
        price_ngn=result.price_ngn,
        estimated_delivery_seconds=result.estimated_delivery_seconds,
    )


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
                detail=(
                    f"Payment already in progress for order {inflight.order_id}."
                    " Complete or cancel it before starting a new one."
                ),
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
        credential = await create_credential(
            session,
            customer_phone=customer.phone,
            order_id=order_id,
            pool_type="paid",
            duration_days=30,
            country=request.country,
        )
        order.styxproxy_credential_id = credential.id
        order.status = "active"
    await session.commit()
    await session.refresh(order)
    await log_audit_event(
        session,
        event_type="order_created",
        phone=customer.phone,
        order_id=order_id,
        details={
            "plan_code": request.plan_code,
            "country": request.country,
            "amount": total_amount,
            "status": order.status,
        },
    )

    # Get customer name and email for customer emails
    customer_name = customer.name if customer else "Customer"
    customer_email = getattr(customer, "email", None)  # Use customer email if available

    # Send admin notification email
    if order.status == "pending":
        await send_new_order_notification(
            order_id=order_id,
            customer_phone=customer.phone,
            plan_code=request.plan_code,
            amount=total_amount,
            currency="NGN",
        )
        # Send order confirmation to customer if email available
        if customer_email:
            try:
                await send_order_confirmation_email(
                    customer_email=customer_email,
                    customer_name=customer_name,
                    order_id=order_id,
                    plan_code=request.plan_code,
                    amount=total_amount,
                    currency="NGN",
                    quantity=request.quantity,
                )
            except Exception:
                pass
    elif order.status == "active":
        # Send ONE combined email: order details + credentials together
        if customer_email:
            cred = None
            if order.styxproxy_credential_id:
                cred_stmt = select(StyxproxyCredential).where(StyxproxyCredential.id == order.styxproxy_credential_id)
                cred_result = await session.execute(cred_stmt)
                cred = cred_result.scalar_one_or_none()
            if cred:
                try:
                    await send_order_active_email(
                        customer_email=customer_email,
                        customer_name=customer_name,
                        order_id=order_id,
                        plan_code=request.plan_code,
                        amount=total_amount,
                        currency="NGN",
                        quantity=request.quantity,
                        bun_username=cred.bun_username,
                        proxy_ip=cred.upstream_proxy_ip or "",
                        proxy_port=cred.upstream_proxy_port or 1080,
                        protocol=cred.protocol or "socks5",
                        expires_at=cred.expires_at or datetime.utcnow(),
                    )
                except Exception:
                    pass
    cred_brief = None
    if order.styxproxy_credential_id:
        cred_stmt = select(StyxproxyCredential).where(StyxproxyCredential.id == order.styxproxy_credential_id)
        cred_result = await session.execute(cred_stmt)
        cred = cred_result.scalar_one_or_none()
        if cred:
            cred_brief = StyxproxyCredentialBrief(
                id=cred.id,
                bun_username=cred.bun_username,
                protocol=cred.protocol or "socks5",
                upstream_proxy_ip=cred.upstream_proxy_ip,
                upstream_proxy_port=cred.upstream_proxy_port,
                status=cred.status,
            )
    return OrderResponse(
        order_id=order.order_id,
        status=order.status,
        plan_type=order.plan_type,
        country=order.country,
        amount_paid_ngn=order.amount_paid_ngn,
        styxproxy_credential=cred_brief,
        created_at=order.created_at,
        expires_at=order.expires_at,
    )


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
        if order.styxproxy_credential_id:
            cred_stmt = select(StyxproxyCredential).where(StyxproxyCredential.id == order.styxproxy_credential_id)
            cred = (await session.execute(cred_stmt)).scalar_one_or_none()
            if cred:
                cred_brief = StyxproxyCredentialBrief(
                    id=cred.id,
                    bun_username=cred.bun_username,
                    protocol=cred.protocol or "socks5",
                    upstream_proxy_ip=cred.upstream_proxy_ip,
                    upstream_proxy_port=cred.upstream_proxy_port,
                    status=cred.status,
                )
        customer = current_user.get("customer")
        results.append(
            OrderResponse(
                order_id=order.order_id,
                status=order.status,
                plan_type=order.plan_type,
                country=order.country,
                amount_paid_ngn=order.amount_paid_ngn,
                styxproxy_credential=cred_brief,
                created_at=order.created_at,
                expires_at=order.expires_at,
                customer_name=customer.name if customer and customer.name else None,
            )
        )
    return results


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: str, session: AsyncSession = Depends(get_session), current_user: dict = Depends(get_current_account)
):
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
    if order.styxproxy_credential_id:
        cred_stmt = select(StyxproxyCredential).where(StyxproxyCredential.id == order.styxproxy_credential_id)
        cred_result = await session.execute(cred_stmt)
        cred = cred_result.scalar_one_or_none()
        if cred:
            rotation_count = getattr(cred, "rotation_count", 0) or 0
            max_rotations = getattr(cred, "max_rotations", 3) or 3
            cred_brief = StyxproxyCredentialBrief(
                id=cred.id,
                bun_username=cred.bun_username,
                protocol=cred.protocol or "socks5",
                upstream_proxy_ip=cred.upstream_proxy_ip,
                upstream_proxy_port=cred.upstream_proxy_port,
                status=cred.status,
            )
    is_renewable = order.status == "active" and order.expires_at is not None
    return OrderResponse(
        order_id=order.order_id,
        status=order.status,
        plan_type=order.plan_type,
        country=order.country,
        amount_paid_ngn=order.amount_paid_ngn,
        styxproxy_credential=cred_brief,
        created_at=order.created_at,
        expires_at=order.expires_at,
        customer_name=customer.name if customer and customer.name else None,
        is_renewable=is_renewable,
        rotation_count=rotation_count,
        max_rotations=max_rotations,
    )


@router.post("/{order_id}/cancel", response_model=OrderCancelResponse)
async def cancel_order(
    order_id: str,
    request: OrderCancelRequest,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_account),
):
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
    if order.styxproxy_credential_id:
        cred_stmt = select(StyxproxyCredential).where(StyxproxyCredential.id == order.styxproxy_credential_id)
        cred_result = await session.execute(cred_stmt)
        cred = cred_result.scalar_one_or_none()
        if cred:
            cred.status = "revoked"
    await session.commit()
    await log_audit_event(
        session,
        event_type="order_cancelled",
        phone=customer.phone,
        order_id=order_id,
        details={"reason": request.reason},
    )

    # Send admin notification for refund request
    await send_refund_request_notification(
        order_id=order_id,
        customer_phone=customer.phone,
        reason=request.reason,
        amount=float(order.amount_paid_ngn or 0),
        currency="NGN",
    )

    return OrderCancelResponse(
        order_id=order_id, status="cancelled", refund_processed=True, refund_amount_ngn=order.amount_paid_ngn
    )


@router.post("/{order_id}/report-dead", response_model=OrderReportDeadResponse)
async def report_dead_ip(
    order_id: str,
    request: OrderReportDeadRequest,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_account),
):
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
    await log_audit_event(
        session,
        event_type="ip_ban_reported",
        phone=customer.phone,
        order_id=order_id,
        details={"screenshot_url": request.screenshot_url, "issue_description": request.issue_description},
    )
    return OrderReportDeadResponse(
        order_id=order_id, ban_reported=True, status="pending_verification", replacement_estimate_hours=24
    )


class RotateResponse(BaseModel):
    order_id: str
    styxproxy_credential: StyxproxyCredentialBrief
    rotation_count: int
    max_rotations: int

    model_config = {"from_attributes": True}


@router.post("/{order_id}/rotate", response_model=RotateResponse)
async def rotate_proxy(
    order_id: str, session: AsyncSession = Depends(get_session), current_user: dict = Depends(get_current_account)
):
    """Rotate Dante credentials (bun_username + bun_password).

    This rotates the Dante layer only -- the upstream provider IP stays the same.
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
    if not order.styxproxy_credential_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No credential to rotate")
    cred_stmt = select(StyxproxyCredential).where(StyxproxyCredential.id == order.styxproxy_credential_id)
    cred_result = await session.execute(cred_stmt)
    cred = cred_result.scalar_one_or_none()
    if not cred:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Credential not found")

    current_count = getattr(cred, "rotation_count", 0) or 0
    if current_count >= MAX_ROTATIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Rotation limit reached ({MAX_ROTATIONS} per proxy)"
        )

    # Call Dante to rotate credentials (same upstream IP, new bun_username + bun_password)
    from app.services import dante as dante_svc

    new_dante = await dante_svc.rotate_credential(
        current_bun_username=cred.bun_username,
        upstream_ip=cred.upstream_proxy_ip or "",
        upstream_port=cred.upstream_proxy_port or 1080,
        expires_at=cred.expires_at or datetime.utcnow(),
    )

    # Update DB with new credentials
    new_hash = get_password_hash(new_dante.new_bun_password)
    cred.bun_username = new_dante.new_bun_username
    cred.password_hash = new_hash
    cred.rotation_count = current_count + 1
    await session.commit()
    await session.refresh(cred)

    await log_audit_event(
        session,
        event_type="dante_rotated",
        phone=customer.phone,
        order_id=order_id,
        details={
            "rotation_count": current_count + 1,
            "old_username": cred.bun_username,
            "new_username": new_dante.new_bun_username,
            "upstream_ip": cred.upstream_proxy_ip,
        },
    )

    # Send new credentials to customer via email
    # Get customer name and email for customer emails
    customer_name = customer.name if customer else "Customer"
    customer_email = getattr(customer, "email", None)

    try:
        if customer_email:
            await send_credentials_rotated_email(
                customer_email=customer_email,
                customer_name=customer_name,
                order_id=order_id,
                new_username=new_dante.new_bun_username,
                proxy_ip=cred.upstream_proxy_ip or "",
                proxy_port=cred.upstream_proxy_port or 1080,
                protocol=cred.protocol or "socks5",
            )
        else:
            # Fallback: no customer email available, skip email
            pass
    except Exception:
        pass

    # Fire n8n webhook for WhatsApp/Telegram delivery
    from app.services.n8n import trigger_credentials_delivered_webhook

    try:
        import asyncio

        asyncio.create_task(
            trigger_credentials_delivered_webhook(
                order_id=order_id,
                tx_ref=order.payment_reference or "",
                phone=order.customer_phone or "",
                channel=order.channel or "web",
                bun_username=new_dante.new_bun_username,
                bun_password=new_dante.new_bun_password,
                proxy_ip=cred.upstream_proxy_ip or "",
                proxy_port=cred.upstream_proxy_port or 1080,
                expires_at=cred.expires_at,
            )
        )
    except Exception:
        pass

    return RotateResponse(
        order_id=order_id,
        styxproxy_credential=StyxproxyCredentialBrief(
            id=cred.id,
            bun_username=cred.bun_username,
            protocol=cred.protocol or "socks5",
            upstream_proxy_ip=cred.upstream_proxy_ip,
            upstream_proxy_port=cred.upstream_proxy_port,
            status=cred.status,
        ),
        rotation_count=cred.rotation_count,
        max_rotations=MAX_ROTATIONS,
    )


# ─── Credential Delivery ─────────────────────────────────────────────────────


class DeliverResponse(BaseModel):
    """Response for manual credential delivery trigger."""

    order_id: str
    webhook_triggered: bool
    message: str


@router.post("/{order_id}/deliver", response_model=DeliverResponse)
async def deliver_credentials(
    order_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_account),
):
    """
    Manual trigger endpoint to send credentials to n8n webhook.

    Useful for testing or retrying failed deliveries.
    POST /api/orders/{order_id}/deliver
    """
    from app.services.n8n import trigger_credentials_delivered_webhook

    customer = current_user["customer"]
    if not customer:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No customer profile found")

    # Get order with credential
    stmt = select(Order).where(Order.order_id == order_id, Order.customer_phone == customer.phone)
    result = await session.execute(stmt)
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    if not order.styxproxy_credential_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No credential found for this order")

    # Get credential
    cred_stmt = select(StyxproxyCredential).where(StyxproxyCredential.id == order.styxproxy_credential_id)
    cred_result = await session.execute(cred_stmt)
    credential = cred_result.scalar_one_or_none()
    if not credential:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Credential not found")

    if not credential.expires_at:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Credential has no expiration date")

    # Trigger webhook
    await trigger_credentials_delivered_webhook(
        order_id=order.order_id,
        tx_ref=order.payment_reference or "",
        phone=order.customer_phone or "",
        channel="whatsapp",
        bun_username=credential.bun_username,
        bun_password="",  # Password not stored in plaintext
        proxy_ip=credential.upstream_proxy_ip or "",
        proxy_port=credential.upstream_proxy_port or 1080,
        expires_at=credential.expires_at,
    )

    await log_audit_event(
        session,
        event_type="credentials_deliver_triggered",
        phone=customer.phone,
        order_id=order_id,
        details={"tx_ref": order.payment_reference},
    )

    return DeliverResponse(
        order_id=order_id,
        webhook_triggered=True,
        message="Credentials delivery webhook triggered successfully",
    )


# ─── Receipt & PDF Endpoints ───────────────────────────────────────────────────

def _hex_to_rgb(hex_color: str):
    """Convert hex color to RGB tuple (0-1 range)."""
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i : i + 2], 16) / 255.0 for i in (0, 2, 4))


PRIMARY_COLOR = _hex_to_rgb("#0AD25A")
BG_COLOR = _hex_to_rgb("#0a0a0a")
CARD_COLOR = _hex_to_rgb("#1a1a1a")
MUTED_COLOR = _hex_to_rgb("#9CA3AF")
DIM_COLOR = _hex_to_rgb("#6B7280")
WHITE_COLOR = _hex_to_rgb("#ffffff")
LIGHT_COLOR = _hex_to_rgb("#D1D5DB")
BORDER_COLOR = _hex_to_rgb("#262626")


async def _build_receipt_data(session: AsyncSession, tx_ref: str) -> Optional[dict]:
    """Fetch order data for receipt by tx_ref (payment reference)."""
    stmt = (
        select(Order, Customer)
        .outerjoin(Customer, Order.customer_phone == Customer.phone)
        .where((Order.tx_ref == tx_ref) | (Order.payment_reference == tx_ref))
        .limit(1)
    )

    result = await session.execute(stmt)
    row = result.first()

    if not row:
        return None

    order, customer = row

    # Get credential if exists
    cred = None
    if order.styxproxy_credential_id:
        cred_stmt = select(StyxproxyCredential).where(StyxproxyCredential.id == order.styxproxy_credential_id)
        cred_result = await session.execute(cred_stmt)
        cred = cred_result.scalar_one_or_none()

    return {
        "order": order,
        "customer": customer,
        "credential": cred,
    }


@router.get("/{tx_ref}/receipt", response_model=ReceiptOrderResponse)
async def get_receipt(
    tx_ref: str,
    session: AsyncSession = Depends(get_session),
):
    """Get order data for public receipt page (no auth required)."""
    # Query by tx_ref or payment_reference
    stmt = (
        select(Order, Customer)
        .outerjoin(Customer, Order.customer_phone == Customer.phone)
        .where((Order.tx_ref == tx_ref) | (Order.payment_reference == tx_ref))
        .limit(1)
    )

    result = await session.execute(stmt)
    row = result.first()

    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    order, customer = row

    # Get credential if exists
    cred_brief = None
    if order.styxproxy_credential_id:
        cred_stmt = select(StyxproxyCredential).where(StyxproxyCredential.id == order.styxproxy_credential_id)
        cred_result = await session.execute(cred_stmt)
        cred = cred_result.scalar_one_or_none()
        if cred:
            cred_brief = StyxproxyCredentialBrief(
                id=cred.id,
                bun_username=cred.bun_username,
                protocol=cred.protocol or "socks5",
                upstream_proxy_ip=cred.upstream_proxy_ip,
                upstream_proxy_port=cred.upstream_proxy_port,
                status=cred.status,
            )

    customer_name = customer.name if customer and customer.name else None

    return ReceiptOrderResponse(
        order_id=order.order_id,
        tx_ref=order.tx_ref or order.payment_reference,
        status=order.status,
        plan_type=order.plan_type,
        plan_code=order.plan_code,
        country=order.country,
        quantity=order.quantity,
        amount_paid_ngn=order.amount_paid_ngn,
        customer_name=customer_name,
        created_at=order.created_at,
        expires_at=order.expires_at,
        styxproxy_credential=cred_brief,
    )


@router.get("/{tx_ref}/pdf")
async def get_receipt_pdf(
    tx_ref: str,
    session: AsyncSession = Depends(get_session),
):
    """Generate and download a dark-themed PDF receipt."""
    from reportlab.pdfgen import canvas as pdf_canvas

    # Query by tx_ref or payment_reference
    from sqlalchemy import select

    from app.models import Customer, Order, StyxproxyCredential

    stmt = (
        select(Order, Customer)
        .outerjoin(Customer, Order.customer_phone == Customer.phone)
        .where((Order.tx_ref == tx_ref) | (Order.payment_reference == tx_ref))
        .limit(1)
    )

    result = await session.execute(stmt)
    row = result.first()

    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")  # noqa: F823

    order, customer = row

    # Get credential if exists
    cred = None
    if order.styxproxy_credential_id:
        cred_stmt = select(StyxproxyCredential).where(StyxproxyCredential.id == order.styxproxy_credential_id)
        cred_result = await session.execute(cred_stmt)
        cred = cred_result.scalar_one_or_none()

    # ── Build PDF with canvas (full dark-theme control) ──────────
    import io as _io

    buffer = _io.BytesIO()
    W, H = A4  # W = 210mm, H = 297mm (A4 portrait, ReportLab bottom-up coords)
    c = pdf_canvas.Canvas(buffer, pagesize=A4)

    def _rgb(hex_str):
        h = hex_str.lstrip("#")
        return tuple(int(h[i : i + 2], 16) / 255.0 for i in (0, 2, 4))

    GREEN = _rgb("#0AD25A")
    BG = _rgb("#0a0a0a")
    CARD = _rgb("#1a1a1a")
    MUTED = _rgb("#9CA3AF")
    DIM = _rgb("#6B7280")
    WHITE = _rgb("#ffffff")
    LIGHT = _rgb("#D1D5DB")
    BORDER = _rgb("#262626")

    # ── Background ────────────────────────────────────────────
    # Register TTF fonts (DejaVu Sans has ₦ glyph; Helvetica doesn't)
    from reportlab.pdfbase import pdfmetrics as _pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont as _TTFont
    try:
        _pdfmetrics.registerFont(_TTFont("DejaVu", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"))
        _pdfmetrics.registerFont(_TTFont("DejaVu-Bold", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"))
        NAIRA_FONT = "DejaVu-Bold"
    except Exception:
        NAIRA_FONT = "Helvetica-Bold"

    c.setFillColorRGB(*BG)
    c.rect(0, 0, W, H, fill=1, stroke=0)

    # ── Top accent bar (4mm green stripe across the top) ─────
    c.setFillColorRGB(*GREEN)
    c.rect(0, H - 4 * mm, W, 4 * mm, fill=1, stroke=0)

    # Use a TOP-DOWN cursor `y_top_mm` that increases as we go down the page.
    # All values stored as mm. We convert to bottom-up POINTS only at the helper boundary.
    from reportlab.lib.units import mm as _mm
    H_mm = H / _mm  # convert page height from points to mm (A4 = 297mm)
    y_top_mm = 4.0  # mm from top, start below the green accent bar

    def _bot_pt(top_mm):
        """Convert top-down cursor (in mm) to bottom-up PDF coord (in points)."""
        return (H_mm - top_mm) * _mm

    def _draw_text(x_mm, top_mm, text, color, font="Helvetica", size=9, align="left"):
        c.setFillColorRGB(*color)
        c.setFont(font, size)
        y_pt = _bot_pt(top_mm)
        x_pt = x_mm * _mm
        if align == "right":
            c.drawRightString(x_pt, y_pt, text)
        elif align == "center":
            c.drawCentredString(x_pt, y_pt, text)
        else:
            c.drawString(x_pt, y_pt, text)

    def _draw_rect(x_mm, top_mm, w_mm, h_mm, fill_color=None, stroke_color=None, radius=0, line_width=0.2):
        """Draw a rectangle whose TOP edge is at top_mm, extending DOWN."""
        bot_mm = top_mm + h_mm  # bottom edge in top-down
        y_bot_pt = _bot_pt(bot_mm)  # bottom-up in points
        if fill_color is not None:
            c.setFillColorRGB(*fill_color)
        if stroke_color is not None:
            c.setStrokeColorRGB(*stroke_color)
        c.setLineWidth(line_width)
        c.roundRect(x_mm * _mm, y_bot_pt, w_mm * _mm, h_mm * _mm, radius * _mm, fill=1 if fill_color else 0, stroke=1 if stroke_color else 0)

    def _draw_line(x1_mm, top1_mm, x2_mm, top2_mm, color, width=0.2):
        c.setStrokeColorRGB(*color)
        c.setLineWidth(width)
        c.line(x1_mm * _mm, _bot_pt(top1_mm), x2_mm * _mm, _bot_pt(top2_mm))

    # ── Header: logo + tagline (left) | PAYMENT RECEIPT (right) ──
    logo_path = get_logo_path("dark")
    if logo_path.exists():
        c.drawImage(
            str(logo_path),
            15 * _mm,
            _bot_pt(y_top_mm + 8),  # logo TOP at y_top_mm, 8mm tall
            width=16 * _mm,
            height=8 * _mm,
            mask="auto",
        )
    else:
        _draw_rect(15, y_top_mm, 8, 8, fill_color=GREEN, radius=1.5)
        _draw_text(19, y_top_mm + 4.5, "S", BG, font="Helvetica-Bold", size=6, align="center")

    # Tagline below the logo
    _draw_text(15, y_top_mm + 9.5, "Anonymous Proxy Service", MUTED, font="Helvetica", size=7)

    # Right-aligned header
    _draw_text(W / _mm - 15, y_top_mm + 5.5, "PAYMENT RECEIPT", GREEN, font="Helvetica-Bold", size=9, align="right")
    _draw_text(W / _mm - 15, y_top_mm + 9, "styxproxy.com", MUTED, font="Helvetica", size=7, align="right")
    _draw_text(W / _mm - 15, y_top_mm + 12.5, f"Issued: {datetime.now().strftime('%B %d, %Y')}", MUTED, font="Helvetica", size=7, align="right")

    y_top_mm += 22  # advance past header block

    # ── Divider line ─────────────────────────────────────────
    _draw_line(15, y_top_mm, W / _mm - 15, y_top_mm, BORDER)
    y_top_mm += 4

    # ── ORDER CONFIRMATION label + Thank you hero ─────────────
    _draw_text(15, y_top_mm, "ORDER CONFIRMATION", MUTED, font="Helvetica-Bold", size=6.5)
    y_top_mm += 4

    customer_name = customer.name.strip() if customer and customer.name else None
    thank_you = f"Thank you, {customer_name}." if customer_name else "Thank you, customer."
    y_top_mm += 8  # breathing room before big text
    thank_you_top_mm = y_top_mm
    _draw_text(15, y_top_mm, thank_you, WHITE, font="Helvetica-Bold", size=22)
    y_top_mm += 11  # height of 22pt text + a bit

    _draw_text(15, y_top_mm, "Your proxy is ready to use. Below are your credentials.", MUTED, font="Helvetica", size=9)

    # FULFILLED pill — right-aligned with thank_you
    status = (order.status or "pending").upper()
    pill_w_mm = 38
    pill_h_mm = 10
    pill_x_mm = W / _mm - 15 - pill_w_mm
    # Vertically center the pill with the thank_you hero text
    pill_top_mm = thank_you_top_mm + (11 - pill_h_mm) / 2
    _draw_rect(pill_x_mm, pill_top_mm, pill_w_mm, pill_h_mm, fill_color=GREEN, radius=5)
    # Text vertically centered in pill: text baseline is roughly font_size * 0.75 above bottom
    text_baseline_mm = pill_top_mm + pill_h_mm / 2 - 3
    _draw_text(pill_x_mm + pill_w_mm / 2, text_baseline_mm, status, BG, font="Helvetica-Bold", size=9, align="center")

    y_top_mm += 8  # breathing room after subtitle

    # ── Order details card ──────────────────────────────────
    order_card_top_mm = y_top_mm
    order_card_h_mm = 36
    _draw_rect(15, order_card_top_mm, W / _mm - 30, order_card_h_mm, fill_color=CARD, radius=3)

    # Inside-card layout: top-down
    row_top_mm = order_card_top_mm + 6

    # Manually draw Row 1 (Transaction Ref | Order ID)
    _draw_text(20, row_top_mm, "TRANSACTION REFERENCE", MUTED, font="Helvetica-Bold", size=6.5)
    _draw_text(W / _mm / 2 + 5, row_top_mm, "ORDER ID", MUTED, font="Helvetica-Bold", size=6.5)
    row_top_mm += 4.5

    oid = order.order_id or "N/A"
    if len(oid) > 22:
        oid = oid[:22] + "…"
    _draw_text(20, row_top_mm, tx_ref, WHITE, font="Helvetica-Bold", size=10)
    _draw_text(W / _mm / 2 + 5, row_top_mm, oid, WHITE, font="Helvetica-Bold", size=10)
    row_top_mm += 5

    _draw_text(20, row_top_mm, "Flutterwave payment reference", DIM, font="Helvetica", size=6)
    _draw_text(W / _mm / 2 + 5, row_top_mm, "Internal order reference", DIM, font="Helvetica", size=6)
    row_top_mm += 3.5

    # Divider
    _draw_line(20, row_top_mm, W / _mm - 20, row_top_mm, BORDER)
    row_top_mm += 4

    # Row 2 (Date | Method)
    _draw_text(20, row_top_mm, "DATE", MUTED, font="Helvetica-Bold", size=6.5)
    _draw_text(W / _mm / 2 + 5, row_top_mm, "METHOD", MUTED, font="Helvetica-Bold", size=6.5)
    row_top_mm += 4.5

    date_str = order.created_at.strftime("%B %d, %Y") if order.created_at else datetime.now().strftime("%B %d, %Y")
    _draw_text(20, row_top_mm, date_str, WHITE, font="Helvetica", size=9)
    _draw_text(W / _mm / 2 + 5, row_top_mm, "Card / Bank / USSD / QR", WHITE, font="Helvetica", size=9)

    y_top_mm = order_card_top_mm + order_card_h_mm + 5  # below the card

    # ── ITEMS section header ─────────────────────────────────
    _draw_text(15, y_top_mm, "ITEMS", MUTED, font="Helvetica-Bold", size=7)
    _draw_text(W / _mm - 45, y_top_mm, "QTY", MUTED, font="Helvetica-Bold", size=7, align="right")
    _draw_text(W / _mm - 15, y_top_mm, "AMOUNT", MUTED, font="Helvetica-Bold", size=7, align="right")
    y_top_mm += 1.5

    # Underline
    _draw_line(15, y_top_mm, W / _mm - 15, y_top_mm, BORDER)
    y_top_mm += 4

    # ── Item row ─────────────────────────────────────────────
    amount = float(order.amount_paid_ngn or 0)
    quantity = order.quantity or 1
    plan_label = f"{order.plan_code or 'Proxy'} - {order.country or 'N/A'}"

    item_top_mm = y_top_mm
    _draw_text(15, item_top_mm, plan_label, WHITE, font="Helvetica", size=10)
    _draw_text(15, item_top_mm + 5, f"{quantity} unit{'s' if quantity != 1 else ''}  |  HTTP/SOCKS5", MUTED, font="Helvetica", size=6.5)
    _draw_text(W / _mm - 45, item_top_mm, str(quantity), WHITE, font="Helvetica", size=10, align="right")
    _draw_text(W / _mm - 15, item_top_mm, f"₦{amount:,.0f}", WHITE, font=NAIRA_FONT, size=10, align="right")
    y_top_mm = item_top_mm + 12

    # ── TOTAL PAID pill (right-aligned, green) ────────────────
    pill_w_mm = 95
    pill_h_mm = 14
    pill_x_mm = W / _mm - 15 - pill_w_mm
    _draw_rect(pill_x_mm, y_top_mm, pill_w_mm, pill_h_mm, fill_color=GREEN, radius=2)
    # Vertically center text inside pill
    _draw_text(pill_x_mm + 6, y_top_mm + pill_h_mm / 2 - 4, "TOTAL PAID", BG, font="Helvetica-Bold", size=10)
    # Amount uses DejaVu-Bold for the ₦ glyph (extra right padding so glyph doesn't clip)
    _draw_text(pill_x_mm + pill_w_mm - 10, y_top_mm + pill_h_mm / 2 - 4.5, f"₦{amount:,.0f}", BG, font=NAIRA_FONT, size=14, align="right")

    y_top_mm += pill_h_mm + 10  # breathing room

    # ── Credentials card (if cred exists) ───────────────────
    if cred:
        _draw_text(15, y_top_mm, "YOUR PROXY CREDENTIALS", GREEN, font="Helvetica-Bold", size=8)
        y_top_mm += 4

        card_top_mm = y_top_mm
        card_h_mm = 70
        card_bottom_mm = card_top_mm + card_h_mm
        _draw_rect(15, card_top_mm, W / _mm - 30, card_h_mm, fill_color=BG, stroke_color=GREEN, radius=3, line_width=0.6)

        # 4 rows × card_h/4 each
        row_h_mm = card_h_mm / 4
        row_top_mm = card_top_mm + 4

        # Row 1: USERNAME | PASSWORD
        _draw_text(20, row_top_mm, "USERNAME", MUTED, font="Helvetica-Bold", size=6.5)
        _draw_text(W / _mm / 2 + 5, row_top_mm, "PASSWORD", MUTED, font="Helvetica-Bold", size=6.5)
        _draw_text(20, row_top_mm + 5, str(cred.bun_username or "N/A"), GREEN, font="Helvetica-Bold", size=10)
        _draw_text(W / _mm / 2 + 5, row_top_mm + 5, str(cred.bun_password or "N/A"), GREEN, font="Helvetica-Bold", size=10)
        _draw_line(20, row_top_mm + row_h_mm - 3, W / _mm - 20, row_top_mm + row_h_mm - 3, BORDER)
        row_top_mm += row_h_mm

        # Row 2: PROXY ADDRESS | PROTOCOL
        _draw_text(20, row_top_mm, "PROXY ADDRESS", MUTED, font="Helvetica-Bold", size=6.5)
        _draw_text(W / _mm / 2 + 5, row_top_mm, "PROTOCOL", MUTED, font="Helvetica-Bold", size=6.5)
        _draw_text(20, row_top_mm + 5, f"{cred.upstream_proxy_ip or 'N/A'}:{cred.upstream_proxy_port or ''}", GREEN, font="Helvetica-Bold", size=10)
        _draw_text(W / _mm / 2 + 5, row_top_mm + 5, "HTTP / SOCKS5", GREEN, font="Helvetica-Bold", size=10)
        _draw_line(20, row_top_mm + row_h_mm - 3, W / _mm - 20, row_top_mm + row_h_mm - 3, BORDER)
        row_top_mm += row_h_mm

        # Row 3: FULL FORMAT (full width)
        _draw_text(20, row_top_mm, "FULL FORMAT", MUTED, font="Helvetica-Bold", size=6.5)
        full_str = (
            f"http://{cred.bun_username or 'user'}:{cred.bun_password or 'pass'}"
            f"@{cred.upstream_proxy_ip or '0.0.0.0'}:{cred.upstream_proxy_port or 8080}"
        )
        _draw_text(20, row_top_mm + 5, full_str, LIGHT, font="Courier", size=8)
        _draw_line(20, row_top_mm + row_h_mm - 3, W / _mm - 20, row_top_mm + row_h_mm - 3, BORDER)
        row_top_mm += row_h_mm

        # Row 4: EXPIRES | AUTO-RENEW
        _draw_text(20, row_top_mm, "EXPIRES", MUTED, font="Helvetica-Bold", size=6.5)
        _draw_text(W / _mm / 2 + 5, row_top_mm, "AUTO-RENEW", MUTED, font="Helvetica-Bold", size=6.5)
        exp_str = cred.expires_at.strftime("%B %d, %Y") if cred.expires_at else "N/A"
        _draw_text(20, row_top_mm + 5, exp_str, WHITE, font="Helvetica", size=9)
        _draw_text(W / _mm / 2 + 5, row_top_mm + 5, "On (manage to disable)", WHITE, font="Helvetica", size=9)

        y_top_mm = card_bottom_mm + 5

    # ── Support section ─────────────────────────────────────
    sup_top_mm = y_top_mm
    sup_h_mm = 22
    _draw_rect(15, sup_top_mm, W / _mm - 30, sup_h_mm, fill_color=CARD, radius=3)

    # Inside the support card
    _draw_text(20, sup_top_mm + 5, "NEED HELP?", MUTED, font="Helvetica-Bold", size=7)
    _draw_text(20, sup_top_mm + 11, "Chat support:", WHITE, font="Helvetica", size=8)
    _draw_text(20, sup_top_mm + 17, "styxproxy.com/contact", GREEN, font="Helvetica-Bold", size=8)

    _draw_text(95, sup_top_mm + 11, "Email:", MUTED, font="Helvetica", size=7)
    _draw_text(95, sup_top_mm + 17, "Web:", MUTED, font="Helvetica", size=7)
    _draw_text(108, sup_top_mm + 11, "oyebiyiayomide30@gmail.com", WHITE, font="Helvetica-Bold", size=8)
    _draw_text(108, sup_top_mm + 17, "styxproxy.com", WHITE, font="Helvetica-Bold", size=8)

    # ── Footer ─────────────────────────────────────────────
    _draw_text(W / _mm / 2, H / _mm - 8, "This receipt was generated automatically. No signature required.", DIM, font="Helvetica", size=6.5, align="center")

    c.showPage()
    c.save()
    buffer.seek(0)

    from fastapi.responses import StreamingResponse

    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=styxproxy-receipt-{tx_ref}.pdf"},
    )
