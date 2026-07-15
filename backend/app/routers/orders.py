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
    PrecheckRequest,
    PrecheckResponse,
    ReceiptOrderResponse,
)
from app.auth import get_current_account
from app.services.credential import create_credential
from app.services.audit import log_audit_event
from app.services.email import send_new_order_notification, send_order_paid_notification, send_refund_request_notification
from app.services.provider import check_availability

router = APIRouter(prefix="/api/orders", tags=["orders"])

PRODUCT_PRICES = {
    "ISP-NG-1": 5000, "ISP-NG-2": 9500, "DC-NG-1": 8000,
    "RESIDENTIAL-UK-1": 12000, "RESIDENTIAL-US-1": 10000,
    "MOBILE-DE-1": 15000, "MOBILE-JP-1": 18000,
}

# Map plan codes to proxy types for provider API
PLAN_TYPE_MAP = {
    "ISP-NG-1": "isp", "ISP-NG-2": "isp",
    "DC-NG-1": "datacenter",
    "RESIDENTIAL-UK-1": "residential", "RESIDENTIAL-US-1": "residential",
    "MOBILE-DE-1": "mobile", "MOBILE-JP-1": "mobile",
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
    country_map = {"NG": "Nigeria", "UK": "United Kingdom", "US": "United States",
                  "DE": "Germany", "JP": "Japan"}
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
    
    # Send admin notification email
    if order.status == "pending":
        await send_new_order_notification(
            order_id=order_id,
            customer_phone=customer.phone,
            plan_code=request.plan_code,
            amount=total_amount,
            currency="NGN",
        )
    elif order.status == "active":
        await send_order_paid_notification(
            order_id=order_id,
            customer_phone=customer.phone,
            plan_code=request.plan_code,
            amount=total_amount,
            currency="NGN",
        )
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
    
    # Send admin notification for refund request
    await send_refund_request_notification(
        order_id=order_id,
        customer_phone=customer.phone,
        reason=request.reason,
        amount=float(order.amount_paid_ngn or 0),
        currency="NGN",
    )
    
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
    if not order.bunche_credential_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No credential to rotate")
    cred_stmt = select(BuncheCredential).where(BuncheCredential.id == order.bunche_credential_id)
    cred_result = await session.execute(cred_stmt)
    cred = cred_result.scalar_one_or_none()
    if not cred:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Credential not found")

    current_count = getattr(cred, "rotation_count", 0) or 0
    if current_count >= MAX_ROTATIONS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Rotation limit reached ({MAX_ROTATIONS} per proxy)")

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
        session, event_type="dante_rotated",
        phone=customer.phone, order_id=order_id,
        details={
            "rotation_count": current_count + 1,
            "old_username": cred.bun_username,
            "new_username": new_dante.new_bun_username,
            "upstream_ip": cred.upstream_proxy_ip,
        },
    )

    # Send new credentials to customer via email
    from app.services.email import send_rotation_notification_email
    try:
        await send_rotation_notification_email(
            customer_email=order.customer_email,
            bun_username=new_dante.new_bun_username,
            bun_password=new_dante.new_bun_password,
            proxy_ip=cred.upstream_proxy_ip or "",
            proxy_port=cred.upstream_proxy_port or 1080,
            order_id=order_id,
        )
    except Exception:
        pass

    # Fire n8n webhook for WhatsApp/Telegram delivery
    from app.services.n8n import trigger_credentials_delivered_webhook
    try:
        import asyncio
        asyncio.create_task(trigger_credentials_delivered_webhook(
            order_id=order_id,
            tx_ref=order.payment_reference or "",
            phone=order.customer_phone or "",
            channel=order.channel or "web",
            bun_username=new_dante.new_bun_username,
            bun_password=new_dante.new_bun_password,
            proxy_ip=cred.upstream_proxy_ip or "",
            proxy_port=cred.upstream_proxy_port or 1080,
            expires_at=cred.expires_at,
        ))
    except Exception:
        pass

    return RotateResponse(
        order_id=order_id,
        bunche_credential=BuncheCredentialBrief(
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
    
    if not order.bunche_credential_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No credential found for this order")
    
    # Get credential
    cred_stmt = select(BuncheCredential).where(BuncheCredential.id == order.bunche_credential_id)
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

import io
from datetime import datetime
from typing import Optional
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.enums import TA_CENTER, TA_RIGHT


def _hex_to_rgb(hex_color: str):
    """Convert hex color to RGB tuple (0-1 range)."""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) / 255.0 for i in (0, 2, 4))


PRIMARY_COLOR = _hex_to_rgb('#0AD25A')
BG_COLOR = _hex_to_rgb('#0a0a0a')
CARD_COLOR = _hex_to_rgb('#1a1a1a')
MUTED_COLOR = _hex_to_rgb('#9CA3AF')
DIM_COLOR = _hex_to_rgb('#6B7280')
WHITE_COLOR = _hex_to_rgb('#ffffff')
LIGHT_COLOR = _hex_to_rgb('#D1D5DB')
BORDER_COLOR = _hex_to_rgb('#262626')


def _build_receipt_data(session: AsyncSession, tx_ref: str) -> Optional[dict]:
    """Fetch order data for receipt by tx_ref (payment reference)."""
    import asyncio
    
    # Run sync SQLAlchemy in async context
    stmt = select(Order, Customer).outerjoin(
        Customer, Order.customer_phone == Customer.phone
    ).where(
        (Order.tx_ref == tx_ref) | (Order.payment_reference == tx_ref)
    ).limit(1)
    
    # Execute synchronously in async context
    result = asyncio.get_event_loop().run_until_complete(session.execute(stmt))
    row = result.first()
    
    if not row:
        return None
    
    order, customer = row
    
    # Get credential if exists
    cred = None
    if order.bunche_credential_id:
        cred_stmt = select(BuncheCredential).where(BuncheCredential.id == order.bunche_credential_id)
        cred_result = asyncio.get_event_loop().run_until_complete(session.execute(cred_stmt))
        cred = cred_result.scalar_one_or_none()
    
    return {
        'order': order,
        'customer': customer,
        'credential': cred,
    }


@router.get("/{tx_ref}/receipt", response_model=ReceiptOrderResponse)
async def get_receipt(
    tx_ref: str,
    session: AsyncSession = Depends(get_session),
):
    """Get order data for public receipt page (no auth required)."""
    import asyncio
    
    # Query by tx_ref or payment_reference
    stmt = select(Order, Customer).outerjoin(
        Customer, Order.customer_phone == Customer.phone
    ).where(
        (Order.tx_ref == tx_ref) | (Order.payment_reference == tx_ref)
    ).limit(1)
    
    result = asyncio.get_event_loop().run_until_complete(session.execute(stmt))
    row = result.first()
    
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    order, customer = row
    
    # Get credential if exists
    cred_brief = None
    if order.bunche_credential_id:
        cred_stmt = select(BuncheCredential).where(BuncheCredential.id == order.bunche_credential_id)
        cred_result = asyncio.get_event_loop().run_until_complete(session.execute(cred_stmt))
        cred = cred_result.scalar_one_or_none()
        if cred:
            cred_brief = BuncheCredentialBrief(
                id=cred.id,
                bun_username=cred.bun_username,
                protocol=cred.protocol or 'socks5',
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
        bunche_credential=cred_brief,
    )


@router.get("/{tx_ref}/pdf")
async def get_receipt_pdf(
    tx_ref: str,
    session: AsyncSession = Depends(get_session),
):
    """Generate and download PDF receipt."""
    import asyncio
    
    # Query by tx_ref or payment_reference
    stmt = select(Order, Customer).outerjoin(
        Customer, Order.customer_phone == Customer.phone
    ).where(
        (Order.tx_ref == tx_ref) | (Order.payment_reference == tx_ref)
    ).limit(1)
    
    result = asyncio.get_event_loop().run_until_complete(session.execute(stmt))
    row = result.first()
    
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    order, customer = row
    
    # Get credential if exists
    cred = None
    if order.bunche_credential_id:
        cred_stmt = select(BuncheCredential).where(BuncheCredential.id == order.bunche_credential_id)
        cred_result = asyncio.get_event_loop().run_until_complete(session.execute(cred_stmt))
        cred = cred_result.scalar_one_or_none()
    
    # Build PDF
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=20*mm, bottomMargin=20*mm)
    story = []
    
    styles = getSampleStyleSheet()
    
    # Title style
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#0AD25A'),
        spaceAfter=10,
    )
    
    # Normal text styles
    normal_white = ParagraphStyle(
        'NormalWhite',
        parent=styles['Normal'],
        textColor=colors.white,
    )
    
    normal_muted = ParagraphStyle(
        'NormalMuted',
        parent=styles['Normal'],
        textColor=colors.HexColor('#9CA3AF'),
        fontSize=10,
    )
    
    # Header
    story.append(Paragraph("PAYMENT RECEIPT", title_style))
    story.append(Paragraph(f"styxproxy.com • {datetime.now().strftime('%B %d, %Y')}", normal_muted))
    story.append(Spacer(1, 20))
    
    # Order info table
    order_data = [
        ['Transaction Reference:', tx_ref],
        ['Order ID:', order.order_id],
        ['Status:', order.status.upper()],
        ['Date:', order.created_at.strftime('%B %d, %Y') if order.created_at else 'N/A'],
    ]
    
    order_table = Table(order_data, colWidths=[60*mm, 120*mm])
    order_table.setStyle(TableStyle([
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#9CA3AF')),
        ('TEXTCOLOR', (1, 0), (1, -1), colors.white),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(order_table)
    story.append(Spacer(1, 20))
    
    # Items section
    story.append(Paragraph("ITEMS", normal_muted))
    
    # Build items from order
    item_name = f"{order.plan_code or 'Proxy'} - {order.country or 'N/A'}"
    quantity = order.quantity or 1
    amount = order.amount_paid_ngn or 0
    
    items_data = [
        [item_name, str(quantity), f"₦{amount:,.0f}"]
    ]
    
    items_table = Table(items_data, colWidths=[120*mm, 30*mm, 40*mm])
    items_table.setStyle(TableStyle([
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica'),
        ('FONTNAME', (1, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('LINEABOVE', (0, 0), (-1, 0), 1, colors.HexColor('#262626')),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 10))
    
    # Total
    story.append(Paragraph(f"<b>TOTAL PAID:</b> ₦{amount:,.0f}", normal_white))
    story.append(Spacer(1, 20))
    
    # Credentials section (if available)
    if cred:
        story.append(Paragraph("YOUR PROXY CREDENTIALS", title_style))
        story.append(Spacer(1, 10))
        
        cred_data = [
            ['Username:', cred.bun_username or 'N/A'],
            ['Password:', '********'],  # Don't expose password
            ['Proxy Address:', f"{cred.upstream_proxy_ip or 'N/A'}:{cred.upstream_proxy_port or 'N/A'}"],
            ['Protocol:', cred.protocol or 'SOCKS5'],
            ['Expires:', cred.expires_at.strftime('%B %d, %Y') if cred.expires_at else 'N/A'],
        ]
        
        cred_table = Table(cred_data, colWidths=[40*mm, 140*mm])
        cred_table.setStyle(TableStyle([
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#9CA3AF')),
            ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#0AD25A')),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(cred_table)
        story.append(Spacer(1, 20))
    
    # Footer
    story.append(Spacer(1, 30))
    story.append(Paragraph(
        "This receipt was generated automatically. No signature required.",
        normal_muted
    ))
    story.append(Paragraph(
        "© 2026 Styxproxy — Anonymous proxy service.",
        normal_muted
    ))
    
    # Build PDF
    doc.build(story)
    
    # Return PDF
    buffer.seek(0)
    
    from fastapi.responses import StreamingResponse
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=styxproxy-receipt-{tx_ref}.pdf"
        }
    )
