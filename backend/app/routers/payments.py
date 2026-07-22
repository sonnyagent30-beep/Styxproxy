"""Payments router."""
import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.schemas import PaymentInitiateRequest, PaymentInitiateResponse, PaymentStatusResponse
from app.auth import get_current_account
from app.services.flutterwave import create_flutterwave_invoice, verify_flutterwave_payment

router = APIRouter(prefix="/api/payments", tags=["payments"])

PRODUCT_PRICES = {"ISP-NG-1": 5000, "ISP-NG-2": 9500, "DC-NG-1": 8000, "RESIDENTIAL-UK-1": 12000, "RESIDENTIAL-US-1": 10000, "MOBILE-DE-1": 15000, "MOBILE-JP-1": 18000}

@router.post("/initiate", response_model=PaymentInitiateResponse, status_code=status.HTTP_201_CREATED)
async def initiate_payment(request: PaymentInitiateRequest, session: AsyncSession = Depends(get_session), current_user: dict = Depends(get_current_account)):
    customer = current_user["customer"]
    if not customer:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No customer profile found")
    price = PRODUCT_PRICES.get(request.plan_code)
    if not price:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid plan code")
    total_amount = price * request.quantity
    try:
        result = await create_flutterwave_invoice(amount=total_amount, customer_email=f"{customer.phone}@styxproxy.com", customer_phone=customer.phone, currency="NGN", callback_url=request.callback_url, description=f"Payment for {request.plan_code}")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to initiate payment: {str(e)}")
    payment_id = str(uuid.uuid4())
    return PaymentInitiateResponse(payment_id=payment_id, checkout_url=result.get("checkout_url", ""), amount_ngn=total_amount, expires_at=datetime.utcnow() + timedelta(minutes=30))

@router.get("/{tx_ref}/status", response_model=PaymentStatusResponse)
async def get_payment_status(tx_ref: str, session: AsyncSession = Depends(get_session), current_user: dict = Depends(get_current_account)):
    customer = current_user["customer"]
    if not customer:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No customer profile found")
    try:
        payment_data = await verify_flutterwave_payment(tx_ref)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to verify payment: {str(e)}")
    return PaymentStatusResponse(tx_ref=tx_ref, status=payment_data.get("status", "unknown"), amount=payment_data.get("amount", 0), currency=payment_data.get("currency", "NGN"))
