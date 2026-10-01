"""Webhooks router — Payment Flow Rewrite (Sprint 025).

Key changes:
- Replay protection via IDEMPOTENCY on the gateway event id, not via a timestamp
  age cap. See the note above MAX_FUTURE_SKEW_SECONDS for why the age cap was
  removed: it could not distinguish a genuine gateway retry from a replay
  attack, because both carry the same original created_at.
- Reject duplicates regardless of age (200 already_processed)
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
from app.services.capture import (
    GATEWAY_STATUS_SUCCESS,
    UNIT_MAJOR,
    UNIT_MINOR,
    gateway_captured_at,
    record_capture,
)
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
# reasoning that a stale timestamp indicated a replay attack. That is wrong, and
# wrong in the most expensive direction: a gateway RETRY re-delivers the original
# event carrying its ORIGINAL created_at, so the timestamp of a genuine retry is
# indistinguishable from the timestamp of a replay. The cap could not tell them
# apart, so it discarded both.
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
# event id with a unique constraint on processed_webhooks.webhook_id:
# is_webhook_processed() / mark_webhook_processed(). A captured payload replayed
# a thousand times fulfils exactly once. That is the correct tool; an age
# comparison never was.
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
    # Single dedupe key used for BOTH the check below and the mark further down.
    # These used to differ when `id` was absent: the check was skipped entirely
    # (falsy webhook_id) while the mark fell back to tx_ref. Now that idempotency
    # is the only replay protection, a key that does not gate the check is a
    # key that does not protect anything.
    webhook_id = str(event_data.get("id") or tx_ref)
    log_ctx.update({"event": event_type, "tx_ref": tx_ref, "webhook_id": webhook_id})

    # Plausibility check — rejects only impossible timestamps (missing,
    # unparseable, or future-dated). Old is fine: a gateway retry carries the
    # original created_at. See the module-level note on MAX_FUTURE_SKEW_SECONDS.
    if not _is_payload_fresh(payload):
        logger.warning("webhook timestamp not plausible", extra=log_ctx)
        await log_audit_event(session, event_type="flutterwave_webhook_replay_rejected", details=log_ctx)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Webhook payload has no plausible timestamp")

    # Duplicate check — the real replay protection
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
            # amount_paid_ngn is the INVOICE amount and is populated on every
            # row, including cancelled/expired/refunded ones. It is not evidence
            # that money was captured — the capture record below is.
            order.amount_paid_ngn = event_data.get("amount")
            # Flutterwave v3 reports `amount` in the MAJOR unit (NGN), same as
            # what we POST to /v3/payments. Do NOT divide by 100 here.
            record_capture(
                order,
                provider="flutterwave",
                gateway_status=GATEWAY_STATUS_SUCCESS,
                gateway_amount=event_data.get("amount"),
                amount_unit=UNIT_MAJOR,
                gateway_reference=tx_ref,
                gateway_currency=event_data.get("currency"),
                gateway_transaction_id=event_data.get("id"),
                captured_at=gateway_captured_at(event_data),
            )
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

    # Mark as processed. Uses the same key as the duplicate check above, so a
    # redelivery is guaranteed to be seen by that check.
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

    # Plausibility check — rejects only impossible timestamps, never merely old
    # ones. Paystack retries for up to 72h, so an age cap here would discard
    # almost every retry it sends.
    if not _is_payload_fresh_epoch(payload):
        logger.warning("Paystack webhook timestamp not plausible", extra=log_ctx)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Webhook payload has no plausible timestamp")

    # Duplicate check — reject ALL duplicates
    if await is_webhook_processed(session, webhook_id):
        logger.info("duplicate Paystack webhook — already processed", extra=log_ctx)
        return {"status": "already_processed", "webhook_id": webhook_id}

    # Order lookup. The primary join is the reference, which is what the
    # gateway echoes back. `provider_order_id` (the gateway's own numeric
    # transaction id) is the fallback for orders whose stored reference never
    # reached the gateway — the defect that made every Paystack order
    # unfulfillable, and the only way an already-created straggler can still be
    # matched and fulfilled.
    from app.models import Order
    order = (await session.execute(select(Order).where(Order.payment_reference == tx_ref))).scalar_one_or_none()
    if order is None and event_data.get("id") is not None:
        provider_tx_id = str(event_data["id"])
        order = (
            await session.execute(
                select(Order).where(
                    Order.provider_order_id == provider_tx_id,
                    Order.provider == "paystack",
                )
            )
        ).scalar_one_or_none()
        if order is not None:
            logger.warning(
                "Paystack webhook matched on provider_order_id — stored reference was wrong",
                extra={**log_ctx, "order_id": order.order_id,
                       "stored_reference": order.payment_reference},
            )
            await log_audit_event(
                session,
                event_type="paystack_webhook_matched_on_provider_order_id",
                order_id=order.order_id,
                details={**log_ctx, "stored_reference": order.payment_reference,
                         "provider_order_id": provider_tx_id},
            )
    if order and order.status == "expired":
        logger.warning("order expired — rejecting Paystack webhook", extra={**log_ctx, "order_id": order.order_id})
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Order has expired")

    if event_type == "charge.success" and tx_ref:
        if order is None:
            # A signed charge.success with no order means a customer paid and we
            # did nothing — the exact failure this handler previously hid behind
            # a bare 200. Surfacing it loudly matters more than the 2xx:
            # Paystack retries non-2xx deliveries (every 3 min for the first 4
            # tries, then hourly for up to 72h), so this gives a late-committing
            # order a real chance to be picked up on retry. Deliberately NOT
            # marking the webhook processed, so the retry is not rejected as a
            # duplicate.
            #
            # The retry loop terminates because Paystack stops retrying after
            # 72h, not because of a local age cap. It used to be bounded by
            # MAX_PAYLOAD_AGE_SECONDS, which meant the 409 path was unreachable
            # in practice for any retry the gateway actually sends — the cap
            # rejected the payload before this branch could ever run.
            logger.error(
                "Paystack charge.success matched no order — payment received but unfulfilled",
                extra={**log_ctx, "provider_tx_id": str(event_data.get("id", "")),
                       "amount_kobo": event_data.get("amount")},
            )
            await log_audit_event(
                session,
                event_type="paystack_webhook_unmatched_charge_success",
                details={**log_ctx, "provider_tx_id": str(event_data.get("id", "")),
                         "amount_kobo": event_data.get("amount"),
                         "action": "no_fulfillment"},
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="No order matches this payment reference",
            )
        if order.status not in ("fulfilled", "active"):
            order.status = "paid"
            # NOTE: amount_paid_ngn records the INVOICE amount and is populated
            # on every row, including cancelled/expired/refunded ones. It is not
            # evidence that money was captured. The capture record below is.
            order.amount_paid_ngn = (event_data.get("amount") or 0) / 100
            # Paystack's `amount` IS the currency SUBUNIT (kobo), so it is
            # normalised to naira here — see UNIT_MINOR. (Flutterwave is the
            # opposite convention; do not "fix" one to match the other.)
            record_capture(
                order,
                provider="paystack",
                gateway_status=GATEWAY_STATUS_SUCCESS,
                gateway_amount=event_data.get("amount"),
                amount_unit=UNIT_MINOR,
                gateway_reference=tx_ref,
                gateway_currency=event_data.get("currency"),
                gateway_transaction_id=event_data.get("id"),
                captured_at=gateway_captured_at(event_data),
            )
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

    # Plausibility check — rejects only impossible timestamps. NOWPayments
    # re-sends an IPN on every status change carrying the original created_at,
    # so a crypto payment sitting in `waiting` for an hour delivers a
    # one-hour-old payload by design.
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
            # NOWPayments settles in crypto, so there is no single fiat figure
            # the gateway "charged" in naira. Amounts here are the crypto amount
            # actually received (see services/nowpayments.py), which is why the
            # capture record stores the gateway's own currency rather than
            # assuming NGN. A confirmed settlement IS capture evidence.
            record_capture(
                order,
                provider="nowpayments",
                gateway_status=GATEWAY_STATUS_SUCCESS,
                gateway_amount=payload.get("actually_paid") or payload.get("pay_amount"),
                amount_unit=UNIT_MAJOR,
                gateway_reference=tx_ref,
                gateway_currency=payload.get("pay_currency"),
                gateway_transaction_id=payload.get("payment_id"),
                captured_at=gateway_captured_at(payload),
            )
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

    # Plausibility check. TheoremReach is not a payment gateway and has no
    # documented retry schedule, but the same logic applies: this only rejects
    # timestamps that could not be real, never merely old ones.
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
