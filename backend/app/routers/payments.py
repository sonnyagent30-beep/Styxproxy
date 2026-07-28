"""Payments router."""

import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_account
from app.database import get_session
from app.schemas import PaymentInitiateRequest, PaymentInitiateResponse, PaymentStatusResponse
from app.services.audit import log_audit_event
from app.services.customer import get_or_create_customer
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


@router.post("/initiate", response_model=PaymentInitiateResponse, status_code=status.HTTP_201_CREATED)
async def initiate_payment(
    request: PaymentInitiateRequest,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_account),
):
    """Initiate payment — supports anonymous checkout.

    Customer resolution delegated to app.services.customer.get_or_create_customer
    so /payments/initiate and /orders/create stay in sync.
    """
    price = PRODUCT_PRICES.get(request.plan_code)
    if not price:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid plan code")
    if not request.customer_email and not request.customer_phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either customer_email or customer_phone is required",
        )

    platform_account = current_user.get("platform_account") if isinstance(current_user, dict) else None
    customer = await get_or_create_customer(
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
