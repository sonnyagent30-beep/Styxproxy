"""Webhooks router."""
import json
from typing import Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_session
from app.config import get_settings
from app.services.flutterwave import verify_flutterwave_signature, is_webhook_processed, mark_webhook_processed, process_payment_webhook
from app.services.audit import log_audit_event
router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])
settings = get_settings()
async def verify_flutterwave_request(request: Request, verif_hash: Optional[str] = Header(None, alias="Verif-Hash")) -> bytes:
    body = await request.body()
    if verif_hash and not verify_flutterwave_signature(body, verif_hash, settings.flutterwave_webhook_secret):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook signature")
    return body
@router.post("/flutterwave", status_code=status.HTTP_200_OK)
async def flutterwave_webhook(request: Request, session: AsyncSession = Depends(get_session), verif_hash: Optional[str] = Header(None, alias="Verif-Hash")):
    body = await verify_flutterwave_request(request, verif_hash)
    try: payload = json.loads(body)
    except json.JSONDecodeError: raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload")
    event_type = payload.get("event")
    event_data = payload.get("data", {})
    event_id = event_data.get("id") or event_type
    if await is_webhook_processed(session, str(event_id)): return {"received": True, "status": "already_processed"}
    try:
        result = await process_payment_webhook(session, payload)
    except Exception as e:
        await log_audit_event(session, event_type="webhook_processing_error", details={"error": str(e), "event_type": event_type})
        await mark_webhook_processed(session, webhook_id=str(event_id), provider="flutterwave", event_type=event_type)
        raise
    await mark_webhook_processed(session, webhook_id=str(event_id), provider="flutterwave", event_type=event_type, metadata=payload)
    await log_audit_event(session, event_type="webhook_processed", details={"event_type": event_type, "result": result})
    return {"received": True, "status": "processed"}
@router.post("/theorem-reach", status_code=status.HTTP_200_OK)
async def theorem_reach_webhook(request: Request, session: AsyncSession = Depends(get_session)):
    body = await request.body()
    try: payload = json.loads(body)
    except json.JSONDecodeError: raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload")
    event_type = payload.get("event")
    event_id = payload.get("survey_transaction_id") or payload.get("id")
    if await is_webhook_processed(session, str(event_id)): return {"received": True, "status": "already_processed"}
    if event_type == "survey_completed":
        survey_data = payload.get("data", {})
        from sqlalchemy import select
        from app.models import PendingTrialSurvey
        stmt = select(PendingTrialSurvey).where(PendingTrialSurvey.survey_token == survey_data.get("survey_token"))
        result = await session.execute(stmt)
        survey = result.scalar_one_or_none()
        if survey:
            survey.status = "completed"
            survey.responses = survey_data.get("responses", {})
            await mark_webhook_processed(session, webhook_id=str(event_id), provider="theorem_reach", event_type=event_type, metadata=payload)
            await session.commit()
    return {"received": True}
