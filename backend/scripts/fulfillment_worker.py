#!/usr/bin/env python3
"""
RQ worker for Styxproxy webhook fulfillment queue.

Handles slow work off the webhook request path:
- create_credential (provider API calls, up to 5 retries)
- trigger_credentials_delivered_webhook (n8n POST)
- Auto-refund on fulfillment failure

Usage:
    python3 fulfillment_worker.py

Runs as systemd service: styxproxy-fulfillment-worker.service
"""

import asyncio
import logging
import sys
import traceback
from datetime import datetime, timezone

import redis.asyncio as redis
from rq import Queue
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
    return redis.from_url(settings.redis_url, decode_responses=True)


async def fulfill_order_job(job_id: str, tx_ref: str, order_id: str, data_payload: dict):
    """
    RQ job: fulfill an order after payment webhook is received.

    This runs asynchronously — the webhook endpoint returns 200 immediately
    and this job handles the slow work (provider API, n8n, refund).
    """
    logger.info(f"[{job_id}] Starting fulfillment for order_id={order_id}, tx_ref={tx_ref}")

    async with AsyncSessionLocal() as db:
        try:
            from sqlalchemy import select
            from app.models import Order
            from app.services.credential import create_credential
            from app.services.audit import log_audit_event

            # ── Load order ────────────────────────────────────────────────
            order = (
                await db.execute(select(Order).where(Order.order_id == order_id))
            ).scalar_one_or_none()

            if not order:
                logger.warning(f"[{job_id}] Order {order_id} not found — skipping")
                return {"status": "order_not_found"}

            # Already fulfilled
            if order.status in ("fulfilled", "active"):
                logger.info(f"[{job_id}] Order {order_id} already fulfilled — skipping")
                return {"status": "already_fulfilled"}

            amount = data_payload.get("amount", 0)

            # ── Fulfill ──────────────────────────────────────────────────
            fulfillment_error = None
            credential = None
            plaintext_password = None

            try:
                credential, plaintext_password = await create_credential(
                    db_session=db,
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
                order.styxproxy_credential_id = credential.id
                order.status = "fulfilled"
                await db.commit()

                # Deliver credentials
                await trigger_credentials_delivered_webhook(
                    order_id=order.order_id,
                    tx_ref=tx_ref,
                    phone=order.customer_phone or "",
                    channel=order.channel or "web",
                    bun_username=credential.styxproxy_username,
                    bun_password=plaintext_password,
                    proxy_ip=credential.upstream_proxy_ip or "",
                    proxy_port=credential.upstream_proxy_port or 1080,
                    expires_at=credential.expires_at,
                )
                logger.info(f"[{job_id}] Fulfillment OK: credential_id={credential.id}")

            except RuntimeError as e:
                # Provider exhausted retries → auto-refund
                fulfillment_error = str(e)
                order.status = "failed_unfulfilled"
                await db.commit()
                logger.error(f"[{job_id}] Fulfillment failed (provider): {fulfillment_error}")

                settings = get_settings()
                try:
                    await _flutterwave_refund(tx_ref, amount, settings.flutterwave_secret_key)
                    order.status = "refunded"
                    order.refund_requested = True
                    order.refund_reason = f"Auto-refund: provider unavailable — {fulfillment_error}"
                    await db.commit()
                    logger.info(f"[{job_id}] Auto-refund issued for {tx_ref}")
                except Exception as refund_error:
                    logger.error(f"[{job_id}] Refund FAILED for {tx_ref}: {refund_error}")

            except Exception as e:
                fulfillment_error = str(e)
                order.status = "failed_manual_review"
                await db.commit()
                logger.error(f"[{job_id}] Fulfillment failed (other): {fulfillment_error}")

            # ── Audit log ───────────────────────────────────────────────
            try:
                await log_audit_event(
                    session=db,
                    user_id=order.user_id,
                    action="payment.fulfilled",
                    resource_type="order",
                    resource_id=order.order_id,
                    metadata={
                        "tx_ref": tx_ref,
                        "status": order.status,
                        "fulfillment_error": fulfillment_error,
                        "credential_id": credential.id if credential else None,
                    },
                )
            except Exception:
                pass

            return {
                "status": order.status,
                "order_id": order_id,
                "fulfillment_error": fulfillment_error,
            }

        except Exception:
            logger.exception(f"[{job_id}] Unhandled exception")
            return {"status": "error", "error": traceback.format_exc()}


# ── RQ Worker bootstrap ──────────────────────────────────────────────────────
if __name__ == "__main__":
    import redis as sync_redis
    from rq import Worker, Queue
    from redis import Redis as SyncRedis

    settings = get_settings()
    redis_url = settings.redis_url

    logger.info("Starting fulfillment worker...")
    conn = SyncRedis.from_url(redis_url, decode_responses=True)
    worker = Worker(["fulfillment"], connection=conn)
    worker.work(with_scheduler=False, burst=False)
