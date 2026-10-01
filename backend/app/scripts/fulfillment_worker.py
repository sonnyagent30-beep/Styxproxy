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

# RFC 2606 reserved domains used for anonymous-checkout placeholders. A send
# addressed here is accepted by the provider and reported as "sent", but it can
# never reach a human — so a delivery to one of these is a silent credential
# loss, not a delivery.
PLACEHOLDER_EMAIL_DOMAINS = ("example.com", "example.org", "example.net")


def _is_placeholder_email(email: str | None) -> bool:
    """True if the address is a non-routable anonymous-checkout placeholder."""
    if not email:
        return True
    domain = email.rsplit("@", 1)[-1].strip().lower()
    return domain in PLACEHOLDER_EMAIL_DOMAINS


def resolve_customer_email(order, data_payload: dict) -> tuple[str | None, str]:
    """Resolve the customer's real email for credential delivery.

    Returns ``(email, source)``; ``email`` is None when no deliverable address
    exists, and ``source`` says where the answer came from for logging.

    The order row is authoritative: it holds the address the customer actually
    typed at checkout. The gateway payload is only a fallback, because its
    ``customer.email`` is whatever was sent to the gateway — for an anonymous
    checkout that is a synthesized ``guest-anond…@example.com`` placeholder, not
    a real address.

    Payload shape is not uniform across providers, and ``data_payload`` is the
    full webhook body as received, so each provider nests differently:

    * Flutterwave — ``data.customer.email``
    * Paystack — ``data.email`` / ``data.customer_email`` (no ``customer`` object)
    * NOWPayments — no customer email at all
    """
    row_email = (getattr(order, "customer_email", None) or "").strip()
    if row_email and not _is_placeholder_email(row_email):
        return row_email, "order.customer_email"

    data = data_payload.get("data") or {}
    if not isinstance(data, dict):
        data = {}

    gateway_email = ""
    customer_obj = data.get("customer")
    if isinstance(customer_obj, dict):
        gateway_email = customer_obj.get("email") or ""
    if not gateway_email:
        gateway_email = data.get("customer_email") or data.get("email") or ""

    gateway_email = gateway_email.strip()
    if gateway_email and not _is_placeholder_email(gateway_email):
        return gateway_email, "gateway_payload"

    # A placeholder or missing address: the customer paid without giving us a
    # real email, so there is nobody to deliver to.
    return None, "none"


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

            # Refund amount for the auto-refund path below.
            #
            # This used to be `data_payload.get("amount", 0)` — a TOP-LEVEL key.
            # No gateway puts the amount there: Flutterwave sends it at
            # `data.amount` and Paystack at `data.amount` (in kobo), so this
            # read always yielded 0 and the auto-refund was issued for NGN 0 —
            # a failed fulfillment marked "refunded" with no money moved and the
            # customer told nothing. The order row is authoritative and is
            # already the source used for the support-ticket notification below,
            # so use it here too.
            amount = float(order.amount_paid_ngn or 0)

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
                # The helper now returns whether the webhook ACTUALLY
                # succeeded. It previously always returned True, so this flag
                # was set unconditionally and the direct-email fallback below
                # could never run — n8n could fail every single time and the
                # worker still logged "delivered".
                n8n_success = False
                try:
                    n8n_success = await trigger_credentials_delivered_webhook(
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
                    if n8n_success:
                        logger.info("n8n webhook delivered", extra=log_ctx)
                    else:
                        logger.warning(
                            "n8n webhook did not succeed — falling back to direct email",
                            extra=log_ctx,
                        )
                except Exception as n8n_err:
                    n8n_success = False
                    logger.error(
                        "n8n webhook failed — falling back to direct email",
                        extra={**log_ctx, "error": str(n8n_err)},
                    )

                # ── Fallback: direct email if n8n failed ──────────────────
                if not n8n_success:
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
                            # send_order_active_email returns EmailResult; it does not
                            # raise on provider failure, so the previous code logged
                            # "fallback email sent" even when Resend rejected the send.
                            # Inspect the result instead of assuming success.
                            if email_result.success:
                                logger.info(
                                    "fallback email sent",
                                    extra={
                                        **log_ctx,
                                        "email": customer_email,
                                        "email_source": email_source,
                                        "message_id": email_result.message_id,
                                    },
                                )
                            else:
                                logger.error(
                                    "fallback email REJECTED by provider — "
                                    "credentials were NOT delivered",
                                    extra={
                                        **log_ctx,
                                        "email": customer_email,
                                        "email_source": email_source,
                                        "status": email_result.status,
                                        "error": email_result.error,
                                    },
                                )
                        except Exception as email_err:
                            logger.error(
                                "fallback email also failed",
                                extra={**log_ctx, "error": str(email_err)},
                            )
                    else:
                        # Previously a silent skip: the customer was marked
                        # fulfilled with credentials minted, but no address was
                        # ever resolved, so nothing reached them and no log line
                        # said so.
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
                if not amount:
                    # Never issue a NGN 0 refund and then mark the order
                    # "refunded" — that reports money returned when none moved.
                    # Leave the order failed_unfulfilled with the reason
                    # recorded so a human can refund it properly.
                    logger.error(
                        "auto-refund skipped: order has no recorded amount",
                        extra={**log_ctx, "order_id": order_id, "error": fulfillment_error},
                    )
                    order.refund_reason = (
                        f"Auto-refund blocked: no recorded amount on order ({fulfillment_error})"
                    )
                    await db.commit()
                else:
                    try:
                        await _flutterwave_refund(tx_ref, amount, settings.flutterwave_secret_key)
                        order.status = "refunded"
                        order.refund_requested = True
                        order.refund_reason = f"Auto-refund: provider unavailable — {fulfillment_error}"
                        await db.commit()
                        logger.info("auto-refund issued", extra={**log_ctx, "amount": amount})
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
