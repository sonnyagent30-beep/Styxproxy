"""Flutterwave service for payment processing."""
import logging
import hmac, hashlib, httpx, uuid
from datetime import datetime
from typing import Optional
from app.config import get_settings
from app.services.n8n import trigger_credentials_delivered_webhook
from app.services.credential import create_credential

logger = logging.getLogger(__name__)
settings = get_settings()
def verify_flutterwave_signature(payload: bytes, signature: str, secret: str) -> bool:
    computed = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(computed, signature)
async def is_webhook_processed(db_session, event_id: str) -> bool:
    from sqlalchemy import select
    from app.models import ProcessedWebhook
    return (await db_session.execute(select(ProcessedWebhook).where(ProcessedWebhook.webhook_id == event_id))).scalar_one_or_none() is not None
async def mark_webhook_processed(db_session, webhook_id: str, provider: str, event_type: str, extra_data: Optional[dict] = None) -> None:
    from app.models import ProcessedWebhook
    processed = ProcessedWebhook(webhook_id=webhook_id, provider=provider, event_type=event_type, extra_data=extra_data)
    db_session.add(processed)
    await db_session.commit()
async def create_flutterwave_invoice(amount: float, customer_email: str, customer_phone: str, currency: str = "NGN", callback_url: Optional[str] = None, description: Optional[str] = None) -> dict:
    tx_ref = f"TXF-{uuid.uuid4().hex[:8].upper()}"
    async with httpx.AsyncClient(timeout=httpx.Timeout(3.0, connect=10.0)) as client:
        try:
            response = await client.post("https://api.flutterwave.com/v3/payments",
                json={"tx_ref": tx_ref, "amount": amount, "currency": currency, "customer": {"email": customer_email, "phone_number": customer_phone}, "customizations": {"title": "Bunche Proxy Service", "description": description or "Proxy service payment"}, "callback_url": callback_url},
                headers={"Authorization": f"Bearer {settings.flutterwave_secret_key}", "Content-Type": "application/json"})
            response.raise_for_status()
            data = response.json()
            return {"payment_id": data.get("data", {}).get("id"), "checkout_url": data.get("data", {}).get("link"), "tx_ref": tx_ref}
        except httpx.HTTPError as e:
            from app.services.audit import log_audit_event
            await log_audit_event(db_session=None, event_type="payment_initiate_failed", details={"error": str(e), "tx_ref": tx_ref})
            raise
async def verify_flutterwave_payment(tx_ref: str) -> dict:
    async with httpx.AsyncClient(timeout=httpx.Timeout(3.0, connect=10.0)) as client:
        try:
            response = await client.get(f"https://api.flutterwave.com/v3/transactions/verify/by-ref/{tx_ref}", headers={"Authorization": f"Bearer {settings.flutterwave_secret_key}"})
            response.raise_for_status()
            return response.json().get("data", {})
        except httpx.HTTPError as e:
            raise
async def process_payment_webhook(db_session, event_data: dict) -> Optional[dict]:
    event_type = event_data.get("event")
    data = event_data.get("data", {})
    if event_type == "charge.completed":
        tx_ref = data.get("tx_ref")
        status = data.get("status")
        if status == "successful":
            if await is_webhook_processed(db_session, tx_ref):
                return {"status": "already_processed"}
            await mark_webhook_processed(db_session, webhook_id=tx_ref, provider="flutterwave", event_type=event_type, extra_data=data)
            from sqlalchemy import select
            from app.models import Order
            order = (await db_session.execute(select(Order).where(Order.payment_reference == tx_ref))).scalar_one_or_none()
            if order:
                order.status = "paid"
                order.amount_paid_ngn = data.get("amount")
                await db_session.commit()
                
                # Full pipeline: provider → test → Dante → DB → n8n notification
                try:
                    # create_credential returns (BuncheCredential, plaintext_password)
                    credential, plaintext_password = await create_credential(
                        db_session=db_session,
                        order_id=order.order_id,
                        customer_phone=order.customer_phone or "",
                        plan_code=order.plan_code or "unknown",
                        country=order.country or "NG",
                        proxy_type="isp",
                        quantity=1,
                        duration_days=30,
                        protocol="socks5",
                        pool_type="paid",
                    )

                    order.bunche_credential_id = credential.id
                    order.status = "fulfilled"
                    await db_session.commit()

                    # Trigger n8n webhook with the plaintext password
                    if credential.expires_at:
                        await trigger_credentials_delivered_webhook(
                            order_id=order.order_id,
                            tx_ref=tx_ref,
                            phone=order.customer_phone or "",
                            channel=order.channel or "web",
                            bun_username=credential.bun_username,
                            bun_password=plaintext_password,
                            proxy_ip=credential.upstream_proxy_ip or "",
                            proxy_port=credential.upstream_proxy_port or 1080,
                            expires_at=credential.expires_at,
                        )
                except Exception as e:
                    from app.services.audit import log_audit_event
                    await log_audit_event(
                        db_session,
                        event_type="credential_creation_failed",
                        phone=order.customer_phone,
                        order_id=order.order_id,
                        details={"error": str(e), "tx_ref": tx_ref},
                    )
                    logger.error(f"Failed to create credential for order {order.order_id}: {e}")
                
                return {"status": "processed", "order_id": order.order_id}
    return {"status": "ignored"}
