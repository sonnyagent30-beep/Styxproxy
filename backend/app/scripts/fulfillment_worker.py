#!/usr/bin/env python3
"""
RQ worker for Styxproxy webhook fulfillment queue.

Payment Flow Rewrite (Sprint 025):
- Reads proxy_type and quantity from the order (not hardcoded)
- credential delivery by email; n8n is notified afterwards and never gates it
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

# The email resolver now lives in app/services/credential_delivery.py, shared
# with the inline fallback in app/services/flutterwave.py. Re-exported here
# because this module is the historical home and its tests import these names
# from here; keeping the aliases means moving the implementation did not break
# callers or the suite.
from app.services.credential_delivery import (  # noqa: E402
    PLACEHOLDER_EMAIL_DOMAINS,
    is_placeholder_email as _is_placeholder_email,
    resolve_customer_email,
)


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
            # Which channel actually emitted the credential, or None. Declared
            # out here so the audit event and the job's return value can always
            # answer "did this customer get their proxy?" without reading logs.
            delivered_via: str | None = None
            delivery_error: str | None = None

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

                # ── Deliver the credential ─────────────────────────────────
                # Email is the delivery channel. The n8n webhook is a
                # NOTIFICATION, never a gate on delivery.
                #
                # This used to be `if not n8n_success: send email`, which made
                # email conditional on a channel that cannot deliver. The live
                # workflow `Sy0H7iuGMaDg1Af5` is Webhook → Parse Payload → Call
                # Charon and has no send node; Charon returns an escalation
                # string with HTTP 200 when Longcat is out of credit (402). So
                # the n8n execution was recorded `success`, `n8n_success` was
                # True, and the email branch was unreachable — the one path
                # that could actually deliver a credential was suppressed by a
                # failure that looked healthy. Verified live 2026-10-01: n8n
                # executions 166/167/168 all `success`, `lastNodeExecuted:
                # "Call Charon"`, customer credentials POSTed to a Charon with
                # `charon_available: false` and `charon_routing.fallback: none`.
                #
                # Design rule this encodes: credential delivery must never
                # depend on an LLM being funded, or on an automation platform
                # being up. Delivery is unconditional; notification is best
                # effort and is reported, never obeyed.
                customer_email, email_source = resolve_customer_email(order, data_payload)

                if customer_email:
                    try:
                        from app.services.email import send_order_active_email

                        email_result = await send_order_active_email(
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
                        # send_order_active_email returns EmailResult and does NOT
                        # raise on provider failure, so the old code logged
                        # "fallback email sent" even when Resend rejected the send.
                        # Inspect the result instead of assuming success.
                        if email_result.success:
                            delivered_via = "email"
                            logger.info(
                                "credential delivered by email",
                                extra={
                                    **log_ctx,
                                    "email": customer_email,
                                    "email_source": email_source,
                                    "message_id": email_result.message_id,
                                },
                            )
                        else:
                            delivery_error = email_result.error or email_result.status
                            logger.error(
                                "credential email REJECTED by provider — NOT delivered",
                                extra={
                                    **log_ctx,
                                    "email": customer_email,
                                    "email_source": email_source,
                                    "status": email_result.status,
                                    "error": email_result.error,
                                },
                            )
                    except Exception as email_err:
                        delivery_error = str(email_err)
                        logger.error(
                            "credential email raised — NOT delivered",
                            extra={
                                **log_ctx,
                                "email": customer_email,
                                "email_source": email_source,
                                "error": str(email_err),
                            },
                        )
                else:
                    # Previously a silent skip. The order is fulfilled with
                    # credentials minted, but nobody was ever reached and no log
                    # line said so.
                    delivery_error = "no_deliverable_email"
                    logger.error(
                        "NO DELIVERABLE EMAIL — order fulfilled and credentials "
                        "minted, but the customer cannot be reached. "
                        "Credentials must be delivered manually.",
                        extra={
                            **log_ctx,
                            "email_source": email_source,
                            "order_row_email": getattr(order, "customer_email", None),
                        },
                    )

                # ── Notify n8n (best effort, never a gate) ─────────────────
                # Fires AFTER delivery and its result is recorded, never obeyed.
                # Previously this ran first and its return value decided whether
                # email happened at all. Ordering it after delivery means a slow
                # or hung n8n cannot delay the credential reaching the customer,
                # and a Charon 402 cannot suppress it.
                try:
                    n8n_ok = await trigger_credentials_delivered_webhook(
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
                    if n8n_ok:
                        logger.info("n8n notified", extra=log_ctx)
                    else:
                        # Loud on purpose. A silently-failing notification is how
                        # this defect hid in the first place: n8n reported success
                        # while delivering nothing at all.
                        logger.warning(
                            "n8n notification failed — delivery is unaffected "
                            "(this workflow has no send node)",
                            extra=log_ctx,
                        )
                except Exception as n8n_err:
                    logger.warning(
                        "n8n notification raised — delivery is unaffected",
                        extra={**log_ctx, "error": str(n8n_err)},
                    )

                if delivered_via is None:
                    # The order is 'fulfilled' in the DB but nothing reached the
                    # customer. Carried in the return value and the audit event so
                    # it is queryable, not only visible in a log.
                    logger.error(
                        "FULFILLED BUT NOT DELIVERED — manual delivery required",
                        extra={
                            **log_ctx,
                            "delivery_error": delivery_error,
                            "email_source": email_source,
                        },
                    )

                logger.info(
                    "fulfillment completed",
                    extra={
                        **log_ctx,
                        "credential_id": credential.id,
                        "proxy_type": proxy_type,
                        "quantity": quantity,
                        "delivered_via": delivered_via,
                        "delivery_error": delivery_error,
                    },
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
                    # Was reading data_payload["data"]["customer"]["email"] and
                    # binding it to customer_email, which this call never uses —
                    # dead code carrying the same wrong assumption as the delivery
                    # path above.
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
                        # The delivery channel, so "fulfilled" is distinguishable
                        # from "delivered" in the audit trail.
                        "delivered_via": delivered_via,
                        "delivery_error": delivery_error,
                    },
                )
            except Exception as e:
                logger.error(f"audit log failed: {e}", extra=log_ctx)

            return {
                "status": order.status,
                "order_id": order_id,
                "fulfillment_error": fulfillment_error,
                # status == "fulfilled" does NOT mean delivered. These two fields
                # are the difference, and they are what QA should assert on
                # (never orders.emails_sent — that is a renewal-reminder counter
                # written only by renewal.py, not a delivery record).
                "delivered_via": delivered_via,
                "delivery_error": delivery_error,
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
