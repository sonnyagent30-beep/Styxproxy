#!/usr/bin/env python3
"""
RQ worker for Styxproxy webhook fulfillment queue.

Payment Flow Rewrite (Sprint 025):
- Reads proxy_type and quantity from the order (not hardcoded)
- n8n fallback to direct email on failure
- Auto-refund with support ticket on fulfillment failure
- Structured logging at every step

Usage:
    python3 fulfillment_worker.py

Runs as systemd service: styxproxy-fulfillment-worker.service
"""

import logging
import sys
import traceback
from datetime import datetime, timedelta, timezone

import redis.asyncio as redis
from rq.worker import Worker

# Setup path
sys.path.insert(0, "/opt/styxproxy/backend")

from app.config import get_settings
from app.database import async_session as AsyncSessionLocal
from app.services.flutterwave import _flutterwave_refund
from app.services.n8n import trigger_credentials_delivered_webhook

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("fulfillment-worker")


def get_redis_conn():
    settings = get_settings()
    return redis.from_url(settings.redis_url)


async def fulfill_order_job(tx_ref: str, order_id: str, data_payload: dict, job_id: str = "rq"):
    """
    RQ job: fulfill an order after payment webhook is received.

    This runs asynchronously — the webhook endpoint returns 200 immediately
    and this job handles the slow work (provider API, n8n, refund).

    Sprint 025: proxy_type and quantity now come from the order, not hardcoded.
    """
    log_ctx = {"job_id": job_id, "order_id": order_id, "tx_ref": tx_ref}
    logger.info("fulfillment started", extra=log_ctx)

    async with AsyncSessionLocal() as db:
        try:
            from sqlalchemy import select
            from app.models import Order
            from app.services.audit import log_audit_event
            from app.services.credential import create_credential

            # ── Load order ────────────────────────────────────────────────
            order = (
                await db.execute(select(Order).where(Order.order_id == order_id))
            ).scalar_one_or_none()

            if not order:
                logger.warning("order not found — skipping", extra=log_ctx)
                return {"status": "order_not_found"}

            # Already fulfilled
            if order.status in ("fulfilled", "active"):
                logger.info("order already fulfilled — skipping", extra=log_ctx)
                return {"status": "already_fulfilled"}

            # ── Resolve plan for correct proxy_type ───────────────────────
            from app.routers.orders import resolve_plan
            plan = await resolve_plan(db, order.plan_code or "", country=order.country or "NG")
            if plan:
                proxy_type = plan.plan_type.lower()
            else:
                # Fallback: extract from plan_code prefix
                proxy_type = (order.plan_code or "isp").split("-")[0].lower()
                logger.warning(
                    "could not resolve plan — using plan_code prefix as proxy_type",
                    extra={**log_ctx, "proxy_type": proxy_type},
                )

            # Quantity from order (not hardcoded)
            quantity = order.quantity or 1

            amount = data_payload.get("amount", 0)

            # ── Fulfill ──────────────────────────────────────────────────
            fulfillment_error = None
            credential = None
            plaintext_password = None

            try:
                # Create the correct number of credentials
                for i in range(quantity):
                    logger.info(
                        f"creating credential {i+1}/{quantity}",
                        extra={**log_ctx, "proxy_type": proxy_type, "index": i},
                    )
                    credential, plaintext_password = await create_credential(
                        db_session=db,
                        order_id=order.order_id,
                        customer_phone=order.customer_phone or "",
                        plan_code=order.plan_code or "unknown",
                        country=order.country or "NG",
                        proxy_type=proxy_type,
                        quantity=1,
                        duration_days=30,
                        protocol="socks5",
                        pool_type="paid",
                    )

                order.styxproxy_credential_id = credential.id
                order.status = "fulfilled"
                await db.commit()

                # ── Deliver credentials via n8n webhook ───────────────────
                n8n_success = False
                try:
                    await trigger_credentials_delivered_webhook(
                        order_id=order.order_id,
                        tx_ref=tx_ref,
                        phone=order.customer_phone or "",
                        channel="web",
                        styxproxy_username=credential.styxproxy_username,
                        styxproxy_password=plaintext_password,
                        proxy_ip=credential.upstream_proxy_ip or "",
                        proxy_port=credential.upstream_proxy_port or 1080,
                        expires_at=credential.expires_at or datetime.now(timezone.utc) + timedelta(days=30),
                        receipt_url=f"https://styxproxy.com/receipt/{tx_ref}",
                    )
                    n8n_success = True
                    logger.info("n8n webhook delivered", extra=log_ctx)
                except Exception as n8n_err:
                    logger.error(
                        "n8n webhook failed — falling back to direct email",
                        extra={**log_ctx, "error": str(n8n_err)},
                    )

                # ── Fallback: direct email if n8n failed ──────────────────
                if not n8n_success:
                    customer_email = data_payload.get("data", {}).get("customer", {}).get("email")
                    if customer_email:
                        try:
                            from app.services.email import send_order_active_email
                            await send_order_active_email(
                                customer_email=customer_email,
                                customer_name=customer_email.split("@")[0],
                                order_id=order.order_id,
                                tx_ref=tx_ref,
                                plan_code=order.plan_code or "unknown",
                                amount=order.amount_paid_ngn or 0,
                                currency="NGN",
                                quantity=quantity,
                                styxproxy_username=credential.styxproxy_username,
                                styxproxy_password=plaintext_password,
                                proxy_ip=credential.upstream_proxy_ip or "",
                                proxy_port=credential.upstream_proxy_port or 1080,
                                protocol="socks5",
                                expires_at=credential.expires_at or datetime.now(timezone.utc) + timedelta(days=30),
                                receipt_url=f"https://styxproxy.com/receipt/{tx_ref}",
                            )
                            logger.info("fallback email sent", extra={**log_ctx, "email": customer_email})
                        except Exception as email_err:
                            logger.error(
                                "fallback email also failed",
                                extra={**log_ctx, "error": str(email_err)},
                            )

                logger.info(
                    "fulfillment completed",
                    extra={**log_ctx, "credential_id": credential.id, "proxy_type": proxy_type, "quantity": quantity},
                )

            except RuntimeError as e:
                # Provider exhausted retries → auto-refund
                fulfillment_error = str(e)
                order.status = "failed_unfulfilled"
                await db.commit()
                logger.error(
                    "fulfillment failed (provider)",
                    extra={**log_ctx, "error": fulfillment_error},
                )

                settings = get_settings()
                try:
                    await _flutterwave_refund(tx_ref, amount, settings.flutterwave_secret_key)
                    order.status = "refunded"
                    order.refund_requested = True
                    order.refund_reason = f"Auto-refund: provider unavailable — {fulfillment_error}"
                    await db.commit()
                    logger.info("auto-refund issued", extra=log_ctx)
                except Exception as refund_error:
                    logger.error(
                        "refund failed — order stays failed_unfulfilled",
                        extra={**log_ctx, "refund_error": str(refund_error)},
                    )

                # Create support ticket
                try:
                    customer_email = data_payload.get("data", {}).get("customer", {}).get("email", "")
                    from app.services.email import send_refund_request_notification
                    await send_refund_request_notification(
                        order_id=order_id,
                        customer_phone=order.customer_phone or "",
                        reason=f"Provider exhausted: {fulfillment_error}",
                        amount=float(order.amount_paid_ngn or 0),
                        currency="NGN",
                    )
                    logger.info("support ticket notification sent", extra=log_ctx)
                except Exception as ticket_err:
                    logger.error(
                        "support ticket notification failed",
                        extra={**log_ctx, "error": str(ticket_err)},
                    )

            except Exception as e:
                fulfillment_error = str(e)
                order.status = "failed_manual_review"
                await db.commit()
                logger.error(
                    "fulfillment failed (other)",
                    extra={**log_ctx, "error": fulfillment_error},
                )

            # ── Audit log ───────────────────────────────────────────────
            try:
                await log_audit_event(
                    db_session=db,
                    event_type="payment.fulfilled",
                    phone=order.customer_phone,
                    order_id=order.order_id,
                    status=order.status,
                    details={
                        "tx_ref": tx_ref,
                        "fulfillment_error": fulfillment_error,
                        "credential_id": credential.id if credential else None,
                        "proxy_type": proxy_type,
                        "quantity": quantity,
                    },
                )
            except Exception as e:
                logger.error(f"audit log failed: {e}", extra=log_ctx)

            return {
                "status": order.status,
                "order_id": order_id,
                "fulfillment_error": fulfillment_error,
            }

        except Exception:
            logger.exception("unhandled exception in fulfillment worker")
            return {"status": "error", "error": traceback.format_exc()}


# ── RQ Worker bootstrap ──────────────────────────────────────────────────────
if __name__ == "__main__":
    from redis import Redis as SyncRedis
    from rq import Worker

    settings = get_settings()
    redis_url = settings.redis_url

    logger.info("Starting fulfillment worker...")
    conn = SyncRedis.from_url(redis_url)
    worker = Worker(["fulfillment"], connection=conn)
    worker.work(with_scheduler=False, burst=False)
