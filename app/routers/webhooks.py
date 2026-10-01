"""Webhooks router — Payment Flow Rewrite (Sprint 025).

Key changes:
- Replay window checks for ALL providers (Paystack, NOWPayments added)
- Reject ALL duplicate webhooks regardless of age (409 Conflict)
- Structured logging at every step
- Order expiry check before fulfillment
"""
import asyncio
import datetime as _dt
import hashlib
import hmac
import json
import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
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

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])

# Maximum tolerated SKEW for a future-dated payload, in seconds. 5 minutes
# absorbs ordinary clock drift between us and the gateway.
MAX_FUTURE_SKEW_SECONDS = 300

# There is deliberately NO maximum age.
#
# An earlier version of this module rejected any payload older than 300s,
# reasoning that a stale timestamp indicated a replay attack. That is wrong: a
# gateway RETRY re-delivers the original event carrying its ORIGINAL created_at,
# so a genuine retry and a replayed capture are identical in the one field the
# cap inspected. The cap could not tell them apart, so it rejected both.
#
#   Flutterwave  3 retries at 30-minute intervals  -> retry #1 is ~1800s old
#   Paystack     3min x4, then hourly for up to 72h  -> retries up to 72h old
#   NOWPayments  re-sends on every status change    -> old created_at throughout
#
# The order was paid, the customer paid real money, and the platform answered 400
# and never fulfilled. The same cap also broke FIRST delivery for any customer
# who took longer than 5 minutes on the checkout page, because created_at is set
# when the charge is created, not when the webhook is sent.
#
# Replay protection is the idempotency layer, which keys on the gateway's own
# event id with a unique constraint on processed_webhooks.webhook_id. A captured
# payload replayed a thousand times fulfils exactly once.
#
# MAX_PAYLOAD_AGE_SECONDS is retained as a name only, so existing imports and
# tests that build a stale timestamp keep working. It no longer gates anything.
MAX_PAYLOAD_AGE_SECONDS = 300  # noqa: N816 - historical name, retained for imports


def _parse_timestamp(value: Any) -> Optional[_dt.datetime]:
    """Parse a provider timestamp into an aware UTC datetime, or None.

    Accepts ISO-8601 strings (Flutterwave, NOWPayments) and epoch seconds or
    milliseconds (Paystack). Returns None for anything unparseable, which callers
    treat as an impossible timestamp and reject.
    """
    if isinstance(value, bool) or value is None:
        return None

    if isinstance(value, (int, float)):
        ts = float(value)
        if ts > 1e12:  # milliseconds
            ts /= 1000
        try:
            return _dt.datetime.fromtimestamp(ts, tz=_dt.timezone.utc)
        except (ValueError, TypeError, OSError, OverflowError):
            return None

    if not isinstance(value, str) or not value.strip():
        return None

    try:
        parsed = _dt.datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=_dt.timezone.utc)
    return parsed


def _is_timestamp_plausible(created_at: Optional[_dt.datetime]) -> bool:
    """Return True unless the timestamp is missing, unparseable, or in the future.

    No lower bound on age. A payload from three hours ago is a normal gateway
    retry; a payload from three days ago is a normal Paystack retry. Idempotency,
    not the clock, decides whether it is processed.
    """
    if created_at is None:
        return False
    age = (_dt.datetime.now(_dt.timezone.utc) - created_at).total_seconds()
    return age >= -MAX_FUTURE_SKEW_SECONDS


def _extract_timestamp(payload: dict, timestamp_key: str = "created_at") -> Optional[_dt.datetime]:
    """Pull the event timestamp out of a provider payload and parse it.

    Tries the nested ``data`` object first (Flutterwave, Paystack), then the top
    level (NOWPayments, which sends a flat body). Returns None when the timestamp
    is absent or unparseable.
    """
    keys = (timestamp_key, "created", "createdAt", "created_at", "paid_at")

    data = payload.get("data")
    sources = [data, payload] if isinstance(data, dict) else [payload]

    for source in sources:
        for key in keys:
            raw = source.get(key)
            if raw:
                return _parse_timestamp(raw)

    return None


def _is_payload_fresh(payload: dict, timestamp_key: str = "created_at") -> bool:
    """Plausibility check for ISO-8601 providers (Flutterwave, NOWPayments).

    Name kept for import compatibility; the semantics are "is this timestamp
    possible", not "is this timestamp recent".
    """
    return _is_timestamp_plausible(_extract_timestamp(payload, timestamp_key))


def _is_payload_fresh_epoch(payload: dict) -> bool:
    """Plausibility check for epoch-timestamp providers (Paystack, NOWPayments)."""
    return _is_timestamp_plausible(_extract_timestamp(payload))


@router.post("/flutterwave", status_code=status.HTTP_200_OK)
async def flutterwave_webhook(
    request: Request,
    verif_hash: Optional[str] = Header(None, alias="Verif-Hash"),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Receive and process Flutterwave payment webhooks."""
    log_ctx = {"provider": "flutterwave"}
    settings = get_settings()
    payload_bytes = await request.body()

    # Verify signature
    if not verif_hash:
        logger.warning("missing Verif-Hash header", extra=log_ctx)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Verif-Hash header")
    if not verify_flutterwave_signature(payload_bytes, verif_hash, settings.flutterwave_webhook_secret):
        logger.warning("invalid Flutterwave signature", extra=log_ctx)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Flutterwave signature")

    try:
        payload = json.loads(payload_bytes)
    except json.JSONDecodeError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload")

    event_type = payload.get("event", "")
    event_data = payload.get("data", {})
    tx_ref = event_data.get("tx_ref", "")
    # Single dedupe key for BOTH the duplicate check and the mark below.
    # These used to diverge when `id` was absent: the check was skipped on a
    # falsy key while the mark fell back to tx_ref, making the mark decorative.
    webhook_id = str(event_data.get("id") or tx_ref)
    log_ctx.update({"event": event_type, "tx_ref": tx_ref, "webhook_id": webhook_id})

    # Plausibility check - rejects only impossible timestamps, never merely old.
    if not _is_payload_fresh(payload):
        logger.warning("webhook timestamp not plausible", extra=log_ctx)
        await log_audit_event(session, event_type="flutterwave_webhook_replay_rejected", details=log_ctx)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Webhook payload has no plausible timestamp")

    # Duplicate check — reject ALL duplicates regardless of age
    if webhook_id and await is_webhook_processed(session, webhook_id):
        logger.info("duplicate webhook — already processed", extra=log_ctx)
        return {"status": "already_processed", "webhook_id": webhook_id}

    # Order expiry check
    from app.models import Order
    order = (await session.execute(select(Order).where(Order.payment_reference == tx_ref))).scalar_one_or_none()
    if order and order.status == "expired":
        logger.warning("order expired — rejecting webhook", extra={**log_ctx, "order_id": order.order_id})
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Order has expired")

    # ── charge.completed (successful) → enqueue fulfillment ──
    if event_type == "charge.completed" and (event_data.get("status") == "successful"):
        if order and order.status not in ("fulfilled", "active"):
            order.status = "paid"
            order.amount_paid_ngn = event_data.get("amount")
            await session.commit()

            try:
                from app.routers._webhook_queue import enqueue_fulfillment
                job_id = await enqueue_fulfillment(tx_ref, order.order_id, payload)
                await log_audit_event(session, event_type="webhook_fulfillment_enqueued", details={**log_ctx, "order_id": order.order_id, "job_id": job_id})
            except Exception as eq_err:
                logger.warning(f"RQ enqueue failed, falling back to inline: {eq_err}", extra=log_ctx)
                await process_payment_webhook(session, payload)

    else:
        # All other events — process inline
        try:
            await process_payment_webhook(session, payload)
        except Exception as e:
            logger.error(f"webhook processing error: {e}", extra=log_ctx)
            await log_audit_event(session, event_type="webhook_processing_error", details={**log_ctx, "error": str(e)})
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Webhook processing failed: {e}")

    # Mark as processed
    await mark_webhook_processed(session, webhook_id=webhook_id or tx_ref, provider="flutterwave", event_type=event_type, extra_data={"tx_ref": tx_ref, "status": event_data.get("status")})
    await log_audit_event(session, event_type=f"webhook_{event_type}", details=log_ctx)

    return {"status": "received", "event": event_type, "webhook_id": webhook_id or tx_ref}


@router.post("/paystack", status_code=status.HTTP_200_OK)
async def paystack_webhook(
    request: Request,
    x_paystack_signature: Optional[str] = Header(None, alias="X-Paystack-Signature"),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Paystack charge.success webhook — same fulfillment path as Flutterwave."""
    log_ctx = {"provider": "paystack"}
    from app.services.paystack import verify_paystack_signature

    settings = get_settings()
    payload_bytes = await request.body()

    if not x_paystack_signature or not verify_paystack_signature(payload_bytes, x_paystack_signature):
        logger.warning("invalid Paystack signature", extra=log_ctx)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Paystack signature")

    try:
        payload = json.loads(payload_bytes)
    except json.JSONDecodeError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload")

    event_type = payload.get("event", "")
    event_data = payload.get("data", {})
    tx_ref = event_data.get("reference", "")
    webhook_id = f"ps_{event_data.get('id', tx_ref)}"
    log_ctx.update({"event": event_type, "tx_ref": tx_ref, "webhook_id": webhook_id})

    # Plausibility check - Paystack retries for up to 72h, so an age cap here
    # would discard almost every retry it sends.
    if not _is_payload_fresh_epoch(payload):
        logger.warning("Paystack webhook timestamp not plausible", extra=log_ctx)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Webhook payload has no plausible timestamp")

    # Duplicate check — reject ALL duplicates
    if await is_webhook_processed(session, webhook_id):
        logger.info("duplicate Paystack webhook — already processed", extra=log_ctx)
        return {"status": "already_processed", "webhook_id": webhook_id}

    # Order expiry check
    from app.models import Order
    order = (await session.execute(select(Order).where(Order.payment_reference == tx_ref))).scalar_one_or_none()
    if order and order.status == "expired":
        logger.warning("order expired — rejecting Paystack webhook", extra={**log_ctx, "order_id": order.order_id})
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Order has expired")

    if event_type == "charge.success" and tx_ref:
        if order and order.status not in ("fulfilled", "active"):
            order.status = "paid"
            order.amount_paid_ngn = (event_data.get("amount") or 0) / 100
            await session.commit()
            try:
                from app.routers._webhook_queue import enqueue_fulfillment
                job_id = await enqueue_fulfillment(tx_ref, order.order_id, payload)
                await log_audit_event(session, event_type="webhook_fulfillment_enqueued", details={**log_ctx, "order_id": order.order_id, "job_id": job_id, "gateway": "paystack"})
            except Exception as eq_err:
                logger.warning(f"RQ enqueue failed for paystack {tx_ref}, inline fallback: {eq_err}", extra=log_ctx)
                await process_payment_webhook(session, {"event": "charge.completed", "data": {"tx_ref": tx_ref, "status": "successful", "amount": order.amount_paid_ngn}})

    await mark_webhook_processed(session, webhook_id=webhook_id or tx_ref, provider="paystack", event_type=event_type, extra_data={"tx_ref": tx_ref, "status": event_data.get("status")})
    await log_audit_event(session, event_type=f"paystack_webhook_{event_type}", details=log_ctx)
    return {"status": "received", "event": event_type}


@router.post("/nowpayments", status_code=status.HTTP_200_OK)
async def nowpayments_ipn(
    request: Request,
    x_nowpayments_sig: Optional[str] = Header(None, alias="x-nowpayments-sig"),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """NOWPayments IPN callback — payment_status.finished/confirmed marks paid."""
    log_ctx = {"provider": "nowpayments"}
    from app.services.nowpayments import verify_nowpayments_signature

    payload_bytes = await request.body()
    if not x_nowpayments_sig or not verify_nowpayments_signature(payload_bytes, x_nowpayments_sig):
        logger.warning("invalid NOWPayments signature", extra=log_ctx)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid NOWPayments signature")

    try:
        payload = json.loads(payload_bytes)
    except json.JSONDecodeError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload")

    payment_status = payload.get("payment_status", "")
    tx_ref = payload.get("order_id", "")
    webhook_id = f"np_{payload.get('payment_id', tx_ref)}"
    log_ctx.update({"payment_status": payment_status, "tx_ref": tx_ref, "webhook_id": webhook_id})

    if not tx_ref:
        return {"status": "ignored", "reason": "no order_id"}

    # Plausibility check - NOWPayments re-sends on every status change with the
    # original created_at, so an old IPN is routine.
    if not _is_payload_fresh_epoch(payload):
        logger.warning("NOWPayments webhook timestamp not plausible", extra=log_ctx)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Webhook payload has no plausible timestamp")

    # Duplicate check — reject ALL duplicates
    if await is_webhook_processed(session, webhook_id):
        logger.info("duplicate NOWPayments webhook — already processed", extra=log_ctx)
        return {"status": "already_processed", "webhook_id": webhook_id}

    # Order expiry check
    from app.models import Order
    order = (await session.execute(select(Order).where(Order.payment_reference == tx_ref))).scalar_one_or_none()
    if order and order.status == "expired":
        logger.warning("order expired — rejecting NOWPayments webhook", extra={**log_ctx, "order_id": order.order_id})
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Order has expired")

    if payment_status in ("finished", "confirmed"):
        if order and order.status not in ("fulfilled", "active"):
            order.status = "paid"
            await session.commit()
            try:
                from app.routers._webhook_queue import enqueue_fulfillment
                job_id = await enqueue_fulfillment(tx_ref, order.order_id, payload)
                await log_audit_event(session, event_type="webhook_fulfillment_enqueued", details={**log_ctx, "order_id": order.order_id, "job_id": job_id, "gateway": "crypto"})
            except Exception as eq_err:
                logger.warning(f"RQ enqueue failed for nowpayments {tx_ref}, inline fallback: {eq_err}", extra=log_ctx)
                await process_payment_webhook(session, {"event": "charge.completed", "data": {"tx_ref": tx_ref, "status": "successful"}})

    await mark_webhook_processed(session, webhook_id=webhook_id or tx_ref, provider="nowpayments", event_type=payment_status, extra_data={"tx_ref": tx_ref, "status": payment_status})
    await log_audit_event(session, event_type=f"nowpayments_ipn_{payment_status}", details=log_ctx)
    return {"status": "received", "payment_status": payment_status}


@router.post("/theorem-reach", status_code=status.HTTP_200_OK)
async def theorem_reach_webhook(
    request: Request,
    session: AsyncSession = Depends(get_session),
    x_signature: Optional[str] = Header(None, alias="X-Signature"),
) -> dict[str, Any]:
    """Receive TheoremReach survey completion webhooks."""
    log_ctx = {"provider": "theorem-reach"}
    settings = get_settings()
    payload_bytes = await request.body()

    if not x_signature:
        logger.warning("missing X-Signature header", extra=log_ctx)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing X-Signature header")
    if not _verify_theorem_reach_signature(payload_bytes, x_signature, settings.theorem_reach_webhook_secret):
        logger.warning("invalid X-Signature", extra=log_ctx)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid X-Signature")

    try:
        payload = json.loads(payload_bytes)
    except json.JSONDecodeError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload")

    # Plausibility check - only rejects timestamps that could not be real.
    timestamp_ms = payload.get("event_metadata", {}).get("timestamp_ms")
    if not timestamp_ms:
        logger.warning("TheoremReach webhook missing timestamp", extra=log_ctx)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Webhook payload has no plausible timestamp")
    try:
        ts = _dt.datetime.fromtimestamp(int(timestamp_ms) / 1000, tz=_dt.timezone.utc)
    except (ValueError, TypeError, OSError, OverflowError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Webhook payload has no plausible timestamp")
    if not _is_timestamp_plausible(ts):
        logger.warning("TheoremReach webhook timestamp is not plausible", extra=log_ctx)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Webhook payload has no plausible timestamp")

    event_type = payload.get("event_type", "")
    details = payload.get("details", {})
    survey_id = details.get("survey_id", "")
    device_id = details.get("user_id", "")
    reward_usd = float(details.get("reward_amount_usd", 1.0))
    log_ctx.update({"event_type": event_type, "survey_id": survey_id})

    # Duplicate check
    if survey_id and await is_webhook_processed(session, survey_id):
        logger.info("duplicate TheoremReach webhook — already processed", extra=log_ctx)
        return {"status": "already_processed", "survey_id": survey_id}

    await log_audit_event(session, event_type=f"theorem_reach_{event_type}", details={**log_ctx, "device_id": device_id, "reward_usd": reward_usd, "country": details.get("country")})

    if event_type == "survey_complete" and device_id:
        from app.services.trial_delivery import process_theorem_reach_trial
        asyncio.create_task(process_theorem_reach_trial(device_id=device_id, survey_id=survey_id, reward_usd=reward_usd, country=details.get("country", "Nigeria")))

    if survey_id:
        await mark_webhook_processed(session, webhook_id=survey_id, provider="theorem-reach", event_type=event_type, extra_data={"device_id": device_id, "reward_usd": reward_usd})

    return {"status": "received", "survey_id": survey_id, "event_type": event_type}


def _verify_theorem_reach_signature(payload_bytes: bytes, signature_header: str, secret: str) -> bool:
    """Verify HMAC-SHA256 signature of the TheoremReach webhook payload."""
    if not signature_header:
        return False
    expected = signature_header.lower()
    if expected.startswith("sha256="):
        expected = expected[7:]
    computed = hmac.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest()
    return hmac.compare_digest(computed, expected)
