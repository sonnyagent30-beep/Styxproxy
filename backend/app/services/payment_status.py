"""
Payment status service — computes customer-facing order status.

The user flow:
1. POST /api/orders → creates pending order, returns order_id
2. Frontend redirects to Flutterwave checkout (payment_reference=tx_ref)
3. Customer pays (or abandons)
4. Frontend polls GET /api/orders/{order_id}/status every 3-5s
5. Service figures out the next_action + whether to include credentials

This module is read-only: it inspects the order + Flutterwave + credential,
does NOT mutate anything. The webhook is what flips status to paid/active.
"""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Order, StyxproxyCredential
from app.schemas_payment_status import OrderPaymentStatus, PaymentStatusCredential
from app.services.proxy_management import (
    PROXY_PORT_HTTP,
    PROXY_PORT_SOCKS5,
    PROXY_PUBLIC_HOST,
    build_curl_http_example,
    build_curl_socks5_example,
    build_python_socks5_example,
)


def _compute_next_action(order: Order, payment_status: str) -> tuple[str, str, Optional[str]]:
    """Return (next_action, user_message, next_action_url) for the given state.

    State machine:
      pending + payment pending       → poll (waiting for customer to pay)
      pending + payment successful    → poll (waiting for webhook)
      paid                            → poll (webhook arrived, credential being provisioned)
      active | fulfilled              → redirect_to_proxy_details (show creds + manage link)
      failed / cancelled / abandoned  → show_failure or show_retry
      expired                         → show_failure

    Note: 'fulfilled' is the legacy name from the Flutterwave webhook path; 'active'
    is set by admin re-fulfill + my new catalog flow. Both mean "ready to use".
    """
    if order.status in ("active", "fulfilled"):
        return (
            "redirect_to_proxy_details",
            "✅ Payment confirmed! Your proxy is ready. Connecting you now…",
            f"/manage/proxy/{order.styxproxy_credential_id}",
        )
    if order.status == "paid":
        return (
            "poll",
            "✅ Payment received — provisioning your proxy (usually <10 seconds)…",
            None,
        )
    if order.status == "cancelled":
        return (
            "show_failure",
            "❌ This order was cancelled. If you were charged, contact support.",
            None,
        )
    if order.status == "failed":
        return (
            "show_retry",
            "❌ Payment failed. Click below to try again with a different method.",
            "/catalog",
        )

    # order.status == "pending"
    if payment_status == "successful":
        # Webhook hasn't fired yet but Flutterwave says success — keep polling
        return (
            "poll",
            "✅ Payment confirmed by Flutterwave — waiting for our system to provision (a few seconds)…",
            None,
        )
    if payment_status == "failed":
        return (
            "show_retry",
            "❌ Payment was declined by your bank. Try a different card or bank.",
            "/catalog",
        )
    if payment_status == "abandoned":
        return (
            "show_retry",
            "⚠️ You closed the payment window before completing. Click below to retry.",
            "/catalog",
        )

    # Default: still pending, keep polling
    return (
        "poll",
        "⏳ Waiting for payment confirmation. Complete the payment in the popup window, then this page will update automatically.",  # noqa: E501
        None,
    )


async def get_order_payment_status(
    session: AsyncSession,
    order_id: str,
    customer_phone: str,
    flutterwave_check: Optional[dict] = None,
) -> Optional[OrderPaymentStatus]:
    """Build the payment status response for the given order.

    Args:
        order_id: The order to look up
        customer_phone: Customer phone (for ownership check; returns None if not theirs)
        flutterwave_check: Optional pre-fetched Flutterwave verification (tx_status, etc.)

    Returns:
        OrderPaymentStatus or None if the order doesn't exist / isn't owned by this customer
    """
    order_result = await session.execute(
        select(Order).where(Order.order_id == order_id)
    )
    order = order_result.scalar_one_or_none()
    if not order:
        return None

    # Security: customer can only see their own orders
    if order.customer_phone != customer_phone:
        return None

    # Map Flutterwave payment status
    payment_status = "pending"
    if flutterwave_check:
        fw_status = flutterwave_check.get("status", "").lower()
        if fw_status in ("successful", "success"):
            payment_status = "successful"
        elif fw_status in ("failed", "error"):
            payment_status = "failed"
        elif fw_status in ("abandoned", "cancelled"):
            payment_status = "abandoned"

    # Compute next action
    next_action, user_message, next_action_url = _compute_next_action(order, payment_status)

    # If order is active OR fulfilled, populate credential
    credential_payload: Optional[PaymentStatusCredential] = None
    if order.status in ("active", "fulfilled") and order.styxproxy_credential_id:
        cred_result = await session.execute(
            select(StyxproxyCredential).where(
                StyxproxyCredential.id == order.styxproxy_credential_id
            )
        )
        cred = cred_result.scalar_one_or_none()
        if cred:
            # Decode password (bytea)
            plaintext_pw = ""
            if cred.styxproxy_password:
                plaintext_pw = (
                    cred.styxproxy_password.decode("utf-8", errors="replace")
                    if isinstance(cred.styxproxy_password, bytes)
                    else str(cred.styxproxy_password)
                )

            credential_payload = PaymentStatusCredential(
                credential_id=cred.id,
                styxproxy_username=cred.styxproxy_username,
                styxproxy_password=plaintext_pw,
                proxy_host=PROXY_PUBLIC_HOST,
                proxy_port_socks5=PROXY_PORT_SOCKS5,
                proxy_port_http=PROXY_PORT_HTTP,
                protocol=cred.protocol or "socks5",
                assigned_static_ip=str(cred.assigned_static_ip) if cred.assigned_static_ip else None,
                curl_socks5_example=build_curl_socks5_example(cred.styxproxy_username, plaintext_pw),
                curl_http_example=build_curl_http_example(cred.styxproxy_username, plaintext_pw),
                python_socks5_example=build_python_socks5_example(cred.styxproxy_username, plaintext_pw),
                manage_url=f"/manage/proxy/{cred.id}",
            )

    return OrderPaymentStatus(
        order_id=order.order_id,
        plan_type=order.plan_type or "unknown",
        plan_code=order.plan_code or "unknown",
        country=order.country or "unknown",
        rotation_mode=order.rotation_mode or "rotating",
        quantity_gb=int(order.data_total_gb) if order.data_total_gb else 0,
        duration_days=0,  # not stored on orders yet, default
        amount_paid_ngn=float(order.amount_paid_ngn) if order.amount_paid_ngn else 0.0,
        currency="NGN",
        order_status=order.status,
        payment_status=payment_status,
        payment_reference=order.tx_ref or order.payment_reference,
        created_at=order.created_at,
        paid_at=order.fulfilled_at,
        fulfilled_at=order.fulfilled_at,
        expires_at=order.expires_at,
        next_action=next_action,
        next_action_url=next_action_url,
        user_message=user_message,
        credential=credential_payload,
    )