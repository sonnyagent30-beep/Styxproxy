"""Webhooks router."""

import logging

logger = logging.getLogger(__name__)


import json
from typing import Any, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_session
from app.services.audit import log_audit_event
from app.services.flutterwave import (
    is_webhook_processed,
    mark_webhook_processed,
    process_payment_webhook,
    verify_flutterwave_signature,
)

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


# Maximum age of a Flutterwave webhook payload before we consider it a replay attack.
# Flutterwave expects endpoints to be hit within seconds of the event firing.
# 5 minutes = 300s gives generous headroom for clock drift + retry latency.
FLUTTERWAVE_MAX_PAYLOAD_AGE_SECONDS = 300


def _is_flutterwave_payload_fresh(payload: dict) -> bool:
    """Return True if the webhook payload is recent enough to be from a live event.

    Flutterwave v3 embeds `data.created_at` as ISO 8601 like "2025-01-15T10:30:00.000Z".

    If created_at is missing (older payload shape), reject conservatively as a
    potential replay attempt. If it parses to a timestamp older than the window,
    reject the payload.
    """
    import datetime as _dt

    created_at_raw = (payload.get("data") or {}).get("created_at")
    if not created_at_raw or not isinstance(created_at_raw, str):
        # Missing timestamp = treat as suspicious. Could be older API version,
        # but conservatively reject so a captured payload without created_at
        # cannot be replayed indefinitely.
        return False
    try:
        # Flutterwave emits "2025-01-15T10:30:00.000Z" (fractional seconds).
        # Tolerate +00:00 vs Z, and missing fractional seconds.
        cleaned = created_at_raw.replace("Z", "+00:00")
        created_at = _dt.datetime.fromisoformat(cleaned)
    except (ValueError, TypeError):
        return False
    if created_at.tzinfo is None:
        # Naive timestamp - assume UTC.
        created_at = created_at.replace(tzinfo=_dt.timezone.utc)
    now = _dt.datetime.now(_dt.timezone.utc)
    age = (now - created_at).total_seconds()
    return 0 <= age <= FLUTTERWAVE_MAX_PAYLOAD_AGE_SECONDS


@router.post("/flutterwave", status_code=status.HTTP_200_OK)
async def flutterwave_webhook(
    request: Request,
    verif_hash: Optional[str] = Header(None, alias="Verif-Hash"),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """
    Receive and process Flutterwave payment webhooks.
    Verifies HMAC signature, checks for duplicate processing,
    and delegates payment confirmation to the payment service.
    """
    settings = get_settings()
    payload_bytes = await request.body()

    # Verify Flutterwave signature — REQUIRED, never accept unsigned webhooks
    if not verif_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Verif-Hash header",
        )
    if not verify_flutterwave_signature(payload_bytes, verif_hash, settings.flutterwave_webhook_secret):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Flutterwave signature",
        )

    # Parse payload
    try:
        payload = json.loads(payload_bytes)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload",
        )

    event_type = payload.get("event", "")
    event_data = payload.get("data", {})
    webhook_id = str(event_data.get("id", ""))
    tx_ref = event_data.get("tx_ref", "")

    # Replay-window check: reject webhooks whose embedded created_at is older
    # than FLUTTERWAVE_MAX_PAYLOAD_AGE_SECONDS. Closes the loop on attacker who
    # captures a valid (payload, signature) pair and replays it indefinitely;
    # the duplicate-processing check alone keeps the state consistent, but
    # this drops the request earlier and surfaces replay attempts in Sentry.
    if not _is_flutterwave_payload_fresh(payload):
        await log_audit_event(
            session,
            event_type="flutterwave_webhook_replay_rejected",
            details={
                "tx_ref": tx_ref,
                "created_at": (event_data or {}).get("created_at"),
                "reason": "stale_or_missing_created_at",
            },
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Webhook payload outside replay window",
        )

    # Check for duplicate processing
    if webhook_id and await is_webhook_processed(session, webhook_id):
        return {"status": "already_processed", "webhook_id": webhook_id}

    # ── charge.completed (successful) → enqueue fulfillment, return immediately ──
    # This moves slow work (provider API, n8n webhook, auto-refund) off the
    # request path so Flutterwave gets a fast 200 and retries don't pile up.
    if event_type == "charge.completed" and (event_data.get("status") == "successful"):
        from sqlalchemy import select

        from app.models import Order

        order = (await session.execute(select(Order).where(Order.payment_reference == tx_ref))).scalar_one_or_none()

        if order and order.status not in ("fulfilled", "active"):
            order.status = "paid"
            order.amount_paid_ngn = event_data.get("amount")
            await session.commit()

            # Enqueue fulfillment job (non-blocking)
            try:
                from app.routers._webhook_queue import enqueue_fulfillment

                job_id = await enqueue_fulfillment(tx_ref, order.order_id, payload)
                await log_audit_event(
                    session,
                    event_type="webhook_fulfillment_enqueued",
                    details={"tx_ref": tx_ref, "order_id": order.order_id, "job_id": job_id},
                )
            except Exception as eq_err:
                # Queue unavailable — fall back to inline processing
                logger.warning(f"RQ enqueue failed, falling back to inline: {eq_err}")
                await process_payment_webhook(session, payload)
        # else: order not found or already fulfilled — acknowledge silently

    else:
        # All other events (refunds, disputes, etc.) — process inline (fast)
        try:
            await process_payment_webhook(session, payload)
        except Exception as e:
            await log_audit_event(
                session,
                event_type="webhook_processing_error",
                details={"error": str(e), "event": event_type, "tx_ref": tx_ref},
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Webhook processing failed: {e}",
            )

    # Mark as processed
    await mark_webhook_processed(
        session,
        webhook_id=webhook_id or tx_ref,
        provider="flutterwave",
        event_type=event_type,
        extra_data={"tx_ref": tx_ref, "status": event_data.get("status")},
    )

    # Log audit event
    await log_audit_event(
        session,
        event_type=f"webhook_{event_type}",
        details={"tx_ref": tx_ref, "status": event_data.get("status")},
    )

    return {"status": "received", "event": event_type, "webhook_id": webhook_id or tx_ref}


# TheoremReach HMAC signature — verified using HMAC-SHA256.
# TheoremReach sends X-Signature: sha256=<hex> on every webhook request.
THEOREM_REACH_MAX_PAYLOAD_AGE_SECONDS = 300


def _is_theorem_reach_payload_fresh(payload: dict) -> bool:
    """Return True if the TheoremReach payload timestamp is recent enough."""
    import datetime as _dt

    # TheoremReach sends event.metadata.timestamp_ms as epoch milliseconds.
    timestamp_ms = payload.get("event_metadata", {}).get("timestamp_ms")
    if not timestamp_ms:
        # No timestamp = treat as suspicious (could be a replay).
        return False
    try:
        ts = _dt.datetime.fromtimestamp(int(timestamp_ms) / 1000, tz=_dt.timezone.utc)
    except (ValueError, TypeError, OSError):
        return False
    now = _dt.datetime.now(_dt.timezone.utc)
    age = (now - ts).total_seconds()
    return 0 <= age <= THEOREM_REACH_MAX_PAYLOAD_AGE_SECONDS


def _verify_theorem_reach_signature(payload_bytes: bytes, signature_header: str, secret: str) -> bool:
    """Verify HMAC-SHA256 signature of the TheoremReach webhook payload.

    TheoremReach sends: X-Signature: sha256=<hex_digest>
    The signed payload is the raw request body.
    """
    import hashlib
    import hmac

    if not signature_header:
        return False
    # Strip "sha256=" prefix if present
    expected = signature_header.lower()
    if expected.startswith("sha256="):
        expected = expected[7:]
    computed = hmac.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest()
    return hmac.compare_digest(computed, expected)


@router.post("/theorem-reach", status_code=status.HTTP_200_OK)
async def theorem_reach_webhook(
    request: Request,
    session: AsyncSession = Depends(get_session),
    x_signature: Optional[str] = Header(None, alias="X-Signature"),
) -> dict[str, Any]:
    """Receive TheoremReach survey completion webhooks.

    Verifies HMAC-SHA256 signature, checks replay window, and triggers
    the trial credential pipeline (DataImpulse → 3proxy port allocation →
    n8n → WhatsApp/Telegram delivery).

    Payload shape (confirmed with TheoremReach integration docs):
    {
        "event_type": "survey_complete",
        "event_metadata": { "timestamp_ms": 1234567890123 },
        "details": {
            "survey_id": "SURVEY-XXXX",
            "user_id": "DEVICE-UUID",
            "reward_amount_usd": 1.00,
            "country": "Nigeria"
        }
    }
    """
    settings = get_settings()
    payload_bytes = await request.body()

    # 1. Verify HMAC signature — reject unsigned requests (SEC finding).
    if not x_signature:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Signature header",
        )
    if not _verify_theorem_reach_signature(payload_bytes, x_signature, settings.theorem_reach_webhook_secret):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid X-Signature — payload may have been tampered with",
        )

    # 2. Parse payload
    try:
        payload = json.loads(payload_bytes)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload",
        )

    # 3. Replay-window check
    if not _is_theorem_reach_payload_fresh(payload):
        await log_audit_event(
            session,
            event_type="theorem_reach_webhook_replay_rejected",
            details={"reason": "stale_or_missing_timestamp"},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Webhook payload outside replay window",
        )

    event_type = payload.get("event_type", "")
    details = payload.get("details", {})
    survey_id = details.get("survey_id", "")
    device_id = details.get("user_id", "")  # TheoremReach calls it user_id, maps to device_id
    reward_usd = float(details.get("reward_amount_usd", 1.0))

    # 4. Duplicate check
    if survey_id and await is_webhook_processed(session, survey_id):
        return {"status": "already_processed", "survey_id": survey_id}

    await log_audit_event(
        session,
        event_type=f"theorem_reach_{event_type}",
        details={
            "survey_id": survey_id,
            "device_id": device_id,
            "reward_usd": reward_usd,
            "country": details.get("country"),
        },
    )

    # 5. Trigger trial delivery pipeline (fire-and-forget from webhook perspective)
    if event_type == "survey_complete" and device_id:
        # Import here to avoid circular imports at module load time.
        from app.services.trial_delivery import process_theorem_reach_trial

        asyncio.create_task(
            process_theorem_reach_trial(
                device_id=device_id,
                survey_id=survey_id,
                reward_usd=reward_usd,
                country=details.get("country", "Nigeria"),
            )
        )

    # 6. Mark processed
    if survey_id:
        await mark_webhook_processed(
            session,
            webhook_id=survey_id,
            provider="theorem-reach",
            event_type=event_type,
            extra_data={"device_id": device_id, "reward_usd": reward_usd},
        )

    return {"status": "received", "survey_id": survey_id, "event_type": event_type}


# asyncio is needed for the fire-and-forget task in the theorem-reach handler
import asyncio  # noqa: E402  (imported here to avoid top-level circular import)


# ─── Paystack ────────────────────────────────────────────────────────────────
@router.post("/paystack", status_code=status.HTTP_200_OK)
async def paystack_webhook(
    request: Request,
    x_paystack_signature: Optional[str] = Header(None, alias="X-Paystack-Signature"),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Paystack charge.success webhook — same fulfillment path as Flutterwave.

    Signature: HMAC-SHA512(secret_key, raw_body) in X-Paystack-Signature.
    """
    from app.services.paystack import verify_paystack_signature

    settings = get_settings()
    payload_bytes = await request.body()

    if not x_paystack_signature or not verify_paystack_signature(payload_bytes, x_paystack_signature):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Paystack signature")

    try:
        payload = json.loads(payload_bytes)
    except json.JSONDecodeError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload")

    event_type = payload.get("event", "")
    event_data = payload.get("data", {})
    tx_ref = event_data.get("reference", "")
    webhook_id = f"ps_{event_data.get('id', tx_ref)}"

    if await is_webhook_processed(session, webhook_id):
        return {"status": "already_processed", "webhook_id": webhook_id}

    if event_type == "charge.success" and tx_ref:
        from sqlalchemy import select

        from app.models import Order

        order = (await session.execute(select(Order).where(Order.payment_reference == tx_ref))).scalar_one_or_none()
        if order and order.status not in ("fulfilled", "active"):
            order.status = "paid"
            order.amount_paid_ngn = (event_data.get("amount") or 0) / 100  # kobo → naira
            await session.commit()
            try:
                from app.routers._webhook_queue import enqueue_fulfillment

                job_id = await enqueue_fulfillment(tx_ref, order.order_id, payload)
                await log_audit_event(
                    session,
                    event_type="webhook_fulfillment_enqueued",
                    details={"tx_ref": tx_ref, "order_id": order.order_id, "job_id": job_id, "gateway": "paystack"},
                )
            except Exception as eq_err:
                logger.warning(f"RQ enqueue failed for paystack {tx_ref}, inline fallback: {eq_err}")
                await process_payment_webhook(
                    session,
                    {
                        "event": "charge.completed",
                        "data": {"tx_ref": tx_ref, "status": "successful", "amount": order.amount_paid_ngn},
                    },
                )

    await mark_webhook_processed(
        session,
        webhook_id=webhook_id or tx_ref,
        provider="paystack",
        event_type=event_type,
        extra_data={"tx_ref": tx_ref, "status": event_data.get("status")},
    )
    await log_audit_event(session, event_type=f"paystack_webhook_{event_type}", details={"tx_ref": tx_ref})
    return {"status": "received", "event": event_type}


# ─── NOWPayments (crypto) ────────────────────────────────────────────────────
NOWPAYMENTS_PAID_STATUSES = {"finished", "confirmed"}


@router.post("/nowpayments", status_code=status.HTTP_200_OK)
async def nowpayments_ipn(
    request: Request,
    x_nowpayments_sig: Optional[str] = Header(None, alias="x-nowpayments-sig"),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """NOWPayments IPN callback — payment_status.finished/confirmed marks paid."""
    from app.services.nowpayments import verify_nowpayments_signature

    payload_bytes = await request.body()
    if not x_nowpayments_sig or not verify_nowpayments_signature(payload_bytes, x_nowpayments_sig):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid NOWPayments signature")

    try:
        payload = json.loads(payload_bytes)
    except json.JSONDecodeError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload")

    payment_status = payload.get("payment_status", "")
    # order_id is the tx_ref we assigned at invoice creation; fall back to order_description parse
    tx_ref = payload.get("order_id", "")
    webhook_id = f"np_{payload.get('payment_id', tx_ref)}"

    if not tx_ref:
        return {"status": "ignored", "reason": "no order_id"}

    if await is_webhook_processed(session, webhook_id):
        return {"status": "already_processed", "webhook_id": webhook_id}

    if payment_status in NOWPAYMENTS_PAID_STATUSES:
        from sqlalchemy import select

        from app.models import Order

        order = (await session.execute(select(Order).where(Order.payment_reference == tx_ref))).scalar_one_or_none()
        if order and order.status not in ("fulfilled", "active"):
            order.status = "paid"
            # Crypto pays USD-equivalent; leave amount_paid_ngn to reconciliation,
            # which prices the order from the plan catalog at fulfillment time.
            await session.commit()
            try:
                from app.routers._webhook_queue import enqueue_fulfillment

                job_id = await enqueue_fulfillment(tx_ref, order.order_id, payload)
                await log_audit_event(
                    session,
                    event_type="webhook_fulfillment_enqueued",
                    details={"tx_ref": tx_ref, "order_id": order.order_id, "job_id": job_id, "gateway": "crypto"},
                )
            except Exception as eq_err:
                logger.warning(f"RQ enqueue failed for nowpayments {tx_ref}, inline fallback: {eq_err}")
                await process_payment_webhook(
                    session,
                    {"event": "charge.completed", "data": {"tx_ref": tx_ref, "status": "successful"}},
                )

    await mark_webhook_processed(
        session,
        webhook_id=webhook_id or tx_ref,
        provider="nowpayments",
        event_type=payment_status,
        extra_data={"tx_ref": tx_ref, "status": payment_status},
    )
    await log_audit_event(session, event_type=f"nowpayments_ipn_{payment_status}", details={"tx_ref": tx_ref})
    return {"status": "received", "payment_status": payment_status}
