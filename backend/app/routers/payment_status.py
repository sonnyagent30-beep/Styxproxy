"""
Payment status router — customer-facing polling endpoint.

GET /api/orders/{order_id}/status

Returns a unified status payload that tells the frontend:
  - Is the order paid?
  - Is the credential ready?
  - What should the customer see / do next?
  - (If active) the SOCKS5 credentials

The frontend hits this every 3-5s after the customer is sent to Flutterwave
checkout. When payment clears and the webhook fires, this endpoint transitions
to status=active and includes the credentials.
"""

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_account
from app.database import get_session
from app.schemas_payment_status import OrderPaymentStatus
from app.services.payment_status import get_order_payment_status

router = APIRouter(prefix="/api/orders", tags=["payment-status"])


@router.get("/{order_id}/status", response_model=OrderPaymentStatus)
async def poll_payment_status(
    order_id: str = Path(..., description="Order ID from POST /api/orders response"),
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_account),
):
    """Poll order + payment status. Returns the next action for the frontend.

    When `next_action == "redirect_to_proxy_details"`, the customer has paid
    and the credential is ready — redirect them to next_action_url.

    When `next_action == "poll"`, keep polling (every 3-5s).

    When `next_action == "show_retry"` or `"show_failure"`, the payment
    didn't go through — let the customer retry or contact support.
    """
    customer = current_user.get("customer")
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No customer profile found. Register via /api/platform/register first.",
        )

    # Try to get authoritative Flutterwave status if payment_reference exists
    flutterwave_check = None
    try:
        # Look up the order first to get tx_ref
        from sqlalchemy import select

        from app.models import Order
        from app.services.flutterwave import verify_flutterwave_payment
        order_result = await session.execute(
            select(Order).where(Order.order_id == order_id)
        )
        order = order_result.scalar_one_or_none()
        if order and order.tx_ref:
            try:
                flutterwave_check = await verify_flutterwave_payment(order.tx_ref)
            except Exception:
                # Flutterwave call failed — fall back to local DB status only
                flutterwave_check = None
    except Exception:
        # If anything in the import/lookup path fails, just continue with DB-only status
        pass

    result = await get_order_payment_status(
        session,
        order_id=order_id,
        customer_phone=customer.phone,
        flutterwave_check=flutterwave_check,
    )

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found. Check the order ID or make sure you own this order.",
        )

    return result