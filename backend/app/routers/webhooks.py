"""Webhooks router."""
import json
from typing import Any, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.config import get_settings
from app.services.flutterwave import (
    verify_flutterwave_signature,
    is_webhook_processed,
    mark_webhook_processed,
    process_payment_webhook,
)
from app.services.audit import log_audit_event
from app.schemas import FlutterwaveWebhookPayload

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


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

    # Verify Flutterwave signature
    if verif_hash and not verify_flutterwave_signature(
        payload_bytes, verif_hash, settings.flutterwave_webhook_secret
    ):
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

    # Check for duplicate processing
    if webhook_id and await is_webhook_processed(session, webhook_id):
        return {"status": "already_processed", "webhook_id": webhook_id}

    # Process the webhook
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
