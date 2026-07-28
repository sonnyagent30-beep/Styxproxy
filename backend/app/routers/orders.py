"""Orders router."""

import random
import string
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from slowapi.util import get_remote_address

# Reportlab imports for PDF generation
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_account
from app.database import get_session
from app.limiter import limiter
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
from app.services.customer import get_or_create_customer
from app.services.email import (
    send_credentials_rotated_email,
    send_new_order_notification,
    send_order_active_email,
    send_order_confirmation_email,
    send_refund_request_notification,
)
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
@limiter.limit("10/minute", key_func=get_remote_address)
async def create_order(
    request: Request,  # Sprint 5: required by slowapi (must be first param)
    body: OrderCreateRequest,  # Sprint 5: renamed from 'request' to avoid shadowing
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_account),
):
    # Get the JWT-resolved customer (existing customers keep their phone)
    customer = current_user.get("customer")
    platform_account = current_user.get("platform_account")
    device_id = current_user.get("device_id")

    # For anonymous checkout — fall back to request body to resolve/create
    # the Customer row (mirrors /payments/initiate). If JWT-derived
    # customer exists, prefer it (real phone + last_used_at history).
    if customer is None:
        customer = await get_or_create_customer(
            session,
            phone=None,
            email=body.customer_email,
            platform_account=platform_account,
        )
        if customer is None:
            # No customer_email supplied AND no JWT customer — reject with
            # the SAME message current behavior used so FE scripts get the
            # same hint.
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No customer profile found",
            )

    price = PRODUCT_PRICES.get(body.plan_code)
    if not price:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid plan code")
    total_amount = price * body.quantity

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
        try:
            credential = await create_credential(
                session,
                customer_phone=customer.phone,
                order_id=order_id,
                pool_type="paid",
                duration_days=30,
                country=request.country,
            )
        except Exception as credential_err:
            # Provider exhausted (5x retry fails in get_provider_proxy).
            # Mark the order for refund: status="refunded", refund_requested=True.
            # We do NOT yet call the Flutterwave refund API — that's a
            # separate ticket (FLUTTERWAVE_WEBHOOK_SECRET plus refund endpoint
            # are both unwired). Marking it here lets admin queue process
            # the actual money movement via existing /admin/orders/{id}/refund.
            order.status = "refunded"
            order.refund_requested = True
            order.refund_reason = (
                f"Auto-refund: provider could not deliver a working proxy after "
                f"5 retries. Underlying error: {type(credential_err).__name__}: {credential_err}"
            )
            await session.commit()

            await log_audit_event(
                session,
                event_type="credential_provider_exhausted",
                phone=customer.phone,
                order_id=order_id,
                details={
                    "plan_code": request.plan_code,
                    "country": request.country,
                    "amount": total_amount,
                    "error": str(credential_err),
                    "auto_refund": True,
                    "flw_refund_pending": True,
                },
            )

            # Notify admin so ops sees the failure immediately.
            try:
                await send_refund_request_notification(
                    order_id=order_id,
                    customer_phone=customer.phone,
                    reason=f"Provider exhausted: {credential_err}",
                    amount=total_amount,
                    currency="NGN",
                )
            except Exception:
                # Notification failure should not block the refund itself.
                pass

            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=(
                    f"Order {order_id} could not be fulfilled — provider unavailable. "
                    "Auto-refund queued. Admin will process your refund within 24 hours."
                ),
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


@router.get("/by-payment-reference/{payment_reference}", response_model=OrderResponse)
async def get_order_by_payment_reference(
    payment_reference: str,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Look up order by the FE-generated payment reference (STX-XXXXXX).

    Used by /thank-you polling. Requires no auth — the payment reference
    itself is a sufficiently strong opaque token (32^6 entropy ≈ 60 bits).
    Bug walk theme-B fix: previously the FE polled /api/orders/{txRef}
    which matched @router.get('/{order_id}') and returned 404 because the
    BE Order.order_id format is ORD-XXXXXX (not STX-). The customer
    spent 5 minutes in Loading spinner before timing out.

    Lookup falls back to Order.tx_ref because Flutterwave webhooks set
    that field for fully-paid orders (the FE txRef and the BE tx_ref
    are different fields; FE generates STX-XXXXXX pre-payment,
    Flutterwave stamps its own internal tx_ref post-payment).

    Returns Order + StyxproxyCredential brief so /thank-you can show the
    customer their credentials without a second round-trip.
    """
    stmt = (
        select(Order)
        .where(
            (Order.payment_reference == payment_reference)
            | (Order.tx_ref == payment_reference)
        )
        .order_by(Order.created_at.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    cred_brief = None
    if order.styxproxy_credential_id:
        cred_stmt = select(StyxproxyCredential).where(
            StyxproxyCredential.id == order.styxproxy_credential_id
        )
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

    # customer_name lookup (optional — anonymous orders don't have it
    # available if customer.row was deleted)
    customer_name = None
    if order.customer_phone:
        cust_stmt = select(Customer).where(Customer.phone == order.customer_phone)
        cust_result = await session.execute(cust_stmt)
        cust = cust_result.scalar_one_or_none()
        if cust and cust.name:
            customer_name = cust.name

    return OrderResponse(
        order_id=order.order_id,
        status=order.status,
        plan_type=order.plan_type,
        country=order.country,
        amount_paid_ngn=order.amount_paid_ngn,
        styxproxy_credential=cred_brief,
        created_at=order.created_at,
        expires_at=order.expires_at,
        customer_name=customer_name,
        is_renewable=order.status == "active" and order.expires_at is not None,
    )


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
        current_styxproxy_username=cred.styxproxy_username,
        upstream_ip=cred.upstream_proxy_ip or "",
        upstream_port=cred.upstream_proxy_port or 1080,
        expires_at=cred.expires_at or datetime.utcnow(),
    )

    # Update DB with new credentials (encrypt the new password at rest)
    cred.styxproxy_username = new_dante.new_styxproxy_username
    cred.set_password(new_dante.new_styxproxy_password)
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
            "old_username": cred.styxproxy_username,
            "new_username": new_dante.new_styxproxy_username,
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
                new_username=new_dante.new_styxproxy_username,
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
                bun_username=new_dante.new_styxproxy_username,
                bun_password=new_dante.new_styxproxy_password,
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

    # ── Build PDF using HTML/CSS (matches email template design) ─────
    from weasyprint import HTML as _WeasyHTML

    from app.services.email import (
        LOGO_DARK_B64,
        _get_base_styles,
    )

    currency = "NGN"
    amount = float(order.amount_paid_ngn or 0)
    quantity = order.quantity or 1
    plan_label = f"{order.plan_code or 'Proxy'} - {order.country or 'N/A'}"
    date_str = order.created_at.strftime("%B %d, %Y") if order.created_at else "—"
    oid = order.order_id or "N/A"
    if cred:
        # The credential model stores styxproxy_password as Fernet ciphertext.
        # get_password() decrypts transparently; returns None if encryption is
        # not configured or ciphertext is tampered.
        cred_username = cred.styxproxy_username or "N/A"
        cred_password_display = cred.get_password() or "N/A"
        cred_ip = cred.upstream_proxy_ip or "N/A"
        cred_port = cred.upstream_proxy_port or 8080
        cred_full = f"http://{cred_username}:{cred_password_display}@{cred_ip}:{cred_port}"
        cred_expires = cred.expires_at.strftime("%B %d, %Y") if cred.expires_at else "N/A"
    else:
        cred_username = cred_password_display = cred_ip = "—"
        cred_port = 0
        cred_full = "—"
        cred_expires = "—"

    base_styles = _get_base_styles()

    # Build credentials block (only if credential exists)
    credentials_html = ""
    if cred:
        credentials_html = f"""
        <div class="credentials-card">
            <div class="credentials-header">YOUR PROXY CREDENTIALS</div>
            <div class="cred-row">
                <span class="cred-label">Username</span>
                <span class="cred-value">{cred_username}</span>
            </div>
            <div class="cred-row">
                <span class="cred-label">Password</span>
                <span class="cred-value">{cred_password_display}</span>
            </div>
            <div class="cred-row">
                <span class="cred-label">Proxy Address</span>
                <span class="cred-value">{cred_ip}:{cred_port}</span>
            </div>
            <div class="cred-row">
                <span class="cred-label">Protocol</span>
                <span class="cred-value">HTTP / SOCKS5</span>
            </div>
            <div class="cred-row">
                <span class="cred-label">Full Format</span>
                <span class="cred-value" style="font-size: 11px;">{cred_full}</span>
            </div>
            <div class="cred-row">
                <span class="cred-label">Expires</span>
                <span class="cred-value">{cred_expires}</span>
            </div>
        </div>"""

    # Receipt-specific style overrides — match the reference PDF look
    receipt_styles = """
        /* Receipt-specific overrides on top of email base styles */
        body { background-color: #000; }
        .accent-bar-top { height: 6px; }
        .accent-bar-bottom { height: 6px; }
        .email-container {
            max-width: 760px;
            padding: 0 24px;
        }
        .header-section {
            padding: 20px 0 16px;
            align-items: flex-start;
        }
        .header-section .logo-section img {
            width: 160px;
            height: auto;
        }
        .logo-subtitle {
            font-size: 10px;
            white-space: nowrap;
        }
        .header-label {
            font-size: 12px;
            letter-spacing: 1.5px;
        }
        .header-sublabel {
            font-size: 9px;
        }
        .divider { margin: 0 0 8px; }
        .main-heading {
            font-size: 24px;
            letter-spacing: -0.5px;
            margin-bottom: 4px;
        }
        .subheading { font-size: 13px; margin-bottom: 12px; }
        .card { padding: 14px 18px; border-radius: 4px; margin: 8px 0; }
        .card-row { padding: 8px 0; }
        .card-label {
            font-size: 10px;
            letter-spacing: 1px;
        }
        .card-value { font-size: 14px; }
        .card-value.card-value-primary {
            color: #0AD25A;
            font-weight: 700;
        }
        .total-pill {
            padding: 14px 20px;
            border-radius: 3px;
            background: #0AD25A;
        }
        .total-label { font-size: 11px; }
        .total-amount { font-size: 18px; color: #000; }
        .credentials-card {
            border: 1.5px solid #0AD25A;
            border-radius: 4px;
            padding: 12px 18px;
        }
        .credentials-header {
            color: #0AD25A;
            font-size: 11px;
            letter-spacing: 1.2px;
            margin-bottom: 4px;
        }
        .cred-row {
            padding: 6px 0;
            display: flex;
            justify-content: space-between;
            align-items: baseline;
        }
        .cred-label {
            font-size: 10px;
            letter-spacing: 1px;
            flex-shrink: 0;
        }
        .cred-value {
            font-family: 'Courier New', Courier, monospace;
            color: #0AD25A;
            font-size: 13px;
            text-align: right;
            margin-left: 16px;
        }
        .support-card {
            padding: 16px 20px;
            border-radius: 4px;
            margin-top: 16px;
        }
        .support-title {
            margin-bottom: 8px;
        }
        .support-row {
            margin-bottom: 4px;
        }
        .footer { font-size: 10px; padding: 12px 0; }
        /* Receipt page layout — single page, A4 */
        @page {
            size: A4;
            margin: 0;
        }
        body {
            margin: 0;
            padding: 0;
        }
        .email-wrapper {
            background-color: #000;
        }
    """

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Styxproxy Receipt — {tx_ref}</title>
    <style>{base_styles}{receipt_styles}</style>
</head>
<body>
    <div class="email-wrapper">
        <div class="email-container">
            <div class="accent-bar-top"></div>
            <div class="header-section">
                <div class="logo-section">
                    <img class="logo-dark" src="data:image/png;base64,{LOGO_DARK_B64}" alt="Styxproxy" width="200" height="58" style="display:block;width:200px;height:auto;">
                    <div class="logo-subtitle">Anonymous Proxy Service</div>
                </div>
                <div>
                    <div class="header-label">PAYMENT RECEIPT</div>
                    <div class="header-sublabel">styxproxy.com</div>
                    <div class="header-sublabel">Issued: {date_str}</div>
                </div>
            </div>
            <div class="divider"></div>

            <div class="content-section">
                <div class="section-label">ORDER CONFIRMATION</div>
                <div class="main-heading">Thank you, customer.</div>
                <div class="subheading">Your proxy is ready to use. Below are your credentials.</div>

                <div class="card">
                    <div class="card-row">
                        <span class="card-label">Transaction Reference</span>
                        <span class="card-value card-value-primary">{tx_ref}</span>
                    </div>
                    <div class="card-row">
                        <span class="card-label">Order ID</span>
                        <span class="card-value">{oid[:24]}{'…' if len(oid) > 24 else ''}</span>
                    </div>
                    <div class="card-row">
                        <span class="card-label">Date</span>
                        <span class="card-value">{date_str}</span>
                    </div>
                    <div class="card-row">
                        <span class="card-label">Method</span>
                        <span class="card-value">Card / Bank / USSD / QR</span>
                    </div>
                </div>

                <div class="items-header">
                    <span class="items-label">ITEMS</span>
                    <span class="items-label" style="text-align: right;">AMOUNT</span>
                </div>
                <div class="item-row">
                    <span class="item-name">{plan_label} × {quantity}</span>
                    <span>{currency} {amount:,.0f}</span>
                </div>

                <div class="total-pill">
                    <span class="total-label">Total Paid</span>
                    <span class="total-amount">{currency} {amount:,.0f}</span>
                </div>

                {credentials_html}

                <div class="support-card">
                    <div class="support-title">NEED HELP?</div>
                    <div class="support-row">
                        <span class="support-label">Chat:</span>
                        <a href="https://styxproxy.com/contact" class="support-link">styxproxy.com/contact</a>
                    </div>
                    <div class="support-row">
                        <span class="support-label">Email:</span>
                        <a href="mailto:support@styxproxy.com" class="support-link">support@styxproxy.com</a>
                    </div>
                    <div class="support-row" style="margin-bottom: 0;">
                        <span class="support-label">Web:</span>
                        <a href="https://styxproxy.com" class="support-link">styxproxy.com</a>
                    </div>
                </div>
            </div>

            <div class="footer">
                <div class="footer-auto">This receipt was generated automatically. No signature required.</div>
                <div class="footer-copyright">© 2026 Styxproxy — Anonymous proxy service for the discerning.</div>
            </div>
            <div class="accent-bar-bottom"></div>
        </div>
    </div>
</body>
</html>"""

    pdf_bytes = _WeasyHTML(string=html).write_pdf()
    import io as _io

    buffer = _io.BytesIO(pdf_bytes or b"")

    from fastapi.responses import StreamingResponse

    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=styxproxy-receipt-{tx_ref}.pdf"},
    )
