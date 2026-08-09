"""Webhooks router."""

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
from app.routers._webhook_queue import enqueue_fulfillment

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

        order = (
            await session.execute(select(Order).where(Order.payment_reference == tx_ref))
        ).scalar_one_or_none()

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


@router.post("/theorem-reach", status_code=status.HTTP_200_OK)
async def theorem_reach_webhook(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Receive TheoremReach survey completion webhooks."""
    try:
        payload = json.loads(await request.body())
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload",
        )

    event_type = payload.get("type", "")
    details = payload.get("details", {})

    await log_audit_event(
        session,
        event_type=f"theorem_reach_{event_type}",
        details={"payload": details},
    )

    return {"status": "received"}
