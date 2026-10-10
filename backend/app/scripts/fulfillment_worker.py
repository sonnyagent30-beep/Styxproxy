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
from app.services.n8n import trigger_credentials_delivered_webhook
from app.services.refunds import GatewayRefundError, refund_at_gateway

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
            from app.services.credential import create_credential, resolve_country_for_credential

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
            # Which channel actually emitted the credential, or None. Declared
            # out here so the audit event and the job's return value can always
            # answer "did this customer get their proxy?" without reading logs.
            delivered_via: str | None = None
            delivery_error: str | None = None

            try:
                # Create the correct number of credentials.
                #
                # DC and ISP are sold per IP: a DC-US-3IP order is THREE proxies
                # and must produce three credential rows, three logins and three
                # addresses. Residential/mobile are sold per GB — `quantity`
                # there is the GB amount, and a single credential is correct.
                #
                # Basket orders (basket_items NOT NULL) carry multiple distinct
                # products in ONE order. Each item in the basket gets its own
                # credential(s) — the customer paid for all of them in one
                # transaction and must receive all of them.
                #
                # Before this fix the loop existed but only the LAST credential
                # was recorded on the order and only the LAST was emailed, while
                # the order was marked `fulfilled`. So a 3-IP customer got three
                # credentials created, one recorded, one emailed, and an order
                # that said fulfilled — delivery actively misstating what was
                # bought.
                created: list[tuple] = []

                if order.basket_items:
                    # Multi-item basket: one credential per basket line item.
                    # Each item may itself be multi-IP (DC/ISP), so we loop
                    # over items and then over the quantity within each item.
                    for item_idx, item in enumerate(order.basket_items):
                        item_plan_code = item.get("plan_code", "unknown")
                        item_proxy_type = (item.get("plan_type") or proxy_type).lower()
                        item_country = item.get("country_code") or order.country or "NG"
                        item_city = item.get("city_name") or order.city_name
                        item_quantity = item.get("quantity", 1)

                        for i in range(item_quantity):
                            logger.info(
                                f"creating credential for basket item {item_idx+1}/{len(order.basket_items)}, proxy {i+1}/{item_quantity}",
                                extra={**log_ctx, "proxy_type": item_proxy_type, "item_index": item_idx, "plan_code": item_plan_code},
                            )
                            cred_i, pw_i = await create_credential(
                                db_session=db,
                                order_id=order.order_id,
                                customer_phone=order.customer_phone or "",
                                plan_code=item_plan_code,
                                country=resolve_country_for_credential(item_country),
                                proxy_type=item_proxy_type,
                                quantity=1,
                                duration_days=30,
                                protocol="socks5",
                                pool_type="paid",
                                targeting_mode=order.targeting_mode or "country_chosen",
                                city=item_city,
                            )
                            created.append((cred_i, pw_i))
                else:
                    # Single-item order (legacy): quantity is the IP count
                    # for DC/ISP, or 1 for residential/mobile (GB is on the
                    # credential, not a loop count).
                    for i in range(quantity):
                        logger.info(
                            f"creating credential {i+1}/{quantity}",
                            extra={**log_ctx, "proxy_type": proxy_type, "index": i},
                        )
                        cred_i, pw_i = await create_credential(
                            db_session=db,
                            order_id=order.order_id,
                            customer_phone=order.customer_phone or "",
                            plan_code=order.plan_code or "unknown",
                            country=resolve_country_for_credential(order.country),
                            proxy_type=proxy_type,
                            quantity=1,
                            duration_days=30,
                            protocol="socks5",
                            pool_type="paid",
                            targeting_mode=order.targeting_mode or "country_chosen",
                            city=order.city_name,
                        )
                        created.append((cred_i, pw_i))

                # A partial create must NOT be reported as fulfilled. If the
                # provider gave us fewer than we asked for, that is a failure the
                # customer paid for and it has to be visible.
                expected_count = sum(item.get("quantity", 1) for item in order.basket_items) if order.basket_items else quantity
                if len(created) != expected_count:
                    raise RuntimeError(
                        f"provider returned {len(created)} credential(s) for a "
                        f"basket with {expected_count} expected — refusing to mark fulfilled"
                    )

                credential, plaintext_password = created[-1]
                # `styxproxy_credential_id` is a single FK, so it keeps pointing
                # at the last row for backwards compatibility. The full set is
                # discoverable via styxproxy_credentials.order_id (1:N).
                order.styxproxy_credential_id = credential.id
                order.status = "fulfilled"

                # Create proxy_items for each credential (Option A: parent order + N child proxy records)
                from app.models import ProxyItem
                for idx, (cred_i, _pw_i) in enumerate(created):
                    proxy_item = ProxyItem(
                        order_id=order.order_id,
                        credential_id=cred_i.id,
                        label=f"Proxy {idx + 1}",
                        status=cred_i.status or "active",
                        expires_at=cred_i.expires_at,
                        plan_type=order.plan_type,
                        plan_code=order.plan_code,
                        country=order.country,
                    )
                    db.add(proxy_item)
                await db.commit()

                # All credentials, for the email. Order matters: proxy 1 of N.
                all_credentials = [
                    {
                        "styxproxy_username": c.styxproxy_username,
                        "styxproxy_password": pw,
                        "proxy_ip": c.upstream_proxy_ip or "",
                        "proxy_port": c.upstream_proxy_port or 1080,
                        "protocol": "socks5",
                        "expires_at": c.expires_at,
                    }
                    for c, pw in created
                ]
                logger.info(
                    f"created {len(created)} credential(s) for order {order_id}",
                    extra={**log_ctx, "created_count": len(created), "expected_count": expected_count},
                )

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
                            # One block per proxy. Without this a 3-IP order
                            # emailed a single credential while the line item
                            # said quantity 3.
                            credentials=all_credentials,
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
                        refund = await refund_at_gateway(
                            order,
                            reason=f"Auto-refund: provider unavailable — {fulfillment_error}",
                        )
                        order.status = "refunded"
                        order.refund_requested = True
                        order.refund_reason = f"Auto-refund: provider unavailable — {fulfillment_error}"
                        order.gateway_refund_id = refund.gateway_refund_id
                        order.gateway_refund_status = refund.gateway_status
                        order.gateway_refund_amount = refund.amount_ngn
                        order.gateway_refunded_at = datetime.now(timezone.utc)
                        await db.commit()
                        logger.info("auto-refund issued", extra={**log_ctx, "amount": amount})
                    except GatewayRefundError as refund_error:
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

            # A job that captured money and delivered nothing must NEVER report
            # success to RQ. Returning a dict here made RQ log "Job OK" while the
            # order sat at `paid` with no credential — which is how two orders
            # (NGN 12,000) sat stranded, one for 9 hours, with every signal green
            # and no alert. Raise on any non-terminal outcome so RQ records
            # `failed`, and mark the order so it is recoverable rather than
            # silently parked at `paid`.
            if order.status not in ("fulfilled", "active"):
                _err = fulfillment_error or delivery_error or order.status
                logger.error(
                    "fulfillment did not complete — raising so RQ records FAILED",
                    extra={**log_ctx, "order_status": order.status, "error": _err},
                )
                try:
                    if order.status in ("paid", "pending"):
                        order.status = "failed_unfulfilled"
                        await db.commit()
                except Exception:
                    logger.exception("could not mark order failed_unfulfilled", extra=log_ctx)
                raise RuntimeError(
                    f"fulfillment incomplete for {order_id}: status={order.status} error={_err}"
                )

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

        except RuntimeError:
            # Already logged and already marked. Re-raise so RQ records failure.
            raise
        except Exception:
            logger.exception("unhandled exception in fulfillment worker")
            # Mark the order so a paid-but-unfulfilled state is visible and
            # recoverable instead of sitting at `paid` forever.
            try:
                if order.status in ("paid", "pending"):
                    order.status = "failed_unfulfilled"
                    await db.commit()
            except Exception:
                logger.exception("could not mark order failed_unfulfilled", extra=log_ctx)
            raise


# ── RQ Worker bootstrap ──────────────────────────────────────────────────────
if __name__ == "__main__":
    import asyncio

    from redis import Redis as SyncRedis
    from rq import Worker

    settings = get_settings()
    redis_url = settings.redis_url

    # ── Load valid countries at startup ────────────────────────────────────
    # The worker does not boot app.main, so the FastAPI lifespan never runs.
    # create_credential() calls get_valid_countries() which raises if the set
    # is not loaded — so this must run before any job is served.
    #
    # This uses a RAW asyncpg connection rather than asyncio.run() over the
    # module-level SQLAlchemy engine. That distinction is the whole point:
    # asyncio.run() creates a new event loop, opens the SHARED engine's pool on
    # it, and then CLOSES that loop. engine.dispose() was never called, so the
    # pooled connections stayed bound to a dead loop — and the first job RQ ran
    # on its own loop grabbed one and died with
    # "Future attached to a different loop". Every first-job-after-restart
    # failed, silently. A raw connection never touches the pool, so it cannot
    # poison it.
    async def _load_countries() -> set[str]:
        import asyncpg

        dsn = (settings.database_url or "").replace("postgresql+asyncpg://", "postgresql://")
        conn = await asyncpg.connect(dsn)
        try:
            rows = await conn.fetch("SELECT code FROM countries")
        finally:
            await conn.close()
        return {str(r["code"]).strip().upper() for r in rows if r["code"]}

    try:
        from app.services.countries import set_valid_countries

        _codes = asyncio.run(_load_countries())
        if not _codes:
            logger.error("FATAL: countries table is empty — refusing to start")
            sys.exit(1)
        set_valid_countries(_codes)
        logger.info("Loaded %d valid country codes at startup", len(_codes))
    except Exception as e:
        logger.error("FATAL: could not load valid countries — %s", e)
        sys.exit(1)

    logger.info("Starting fulfillment worker...")
    conn = SyncRedis.from_url(redis_url)
    worker = Worker(["fulfillment"], connection=conn)
    worker.work(with_scheduler=False, burst=False)
