"""Trials router."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_session
from app.schemas import TrialClaimRequest, TrialClaimResponse, TrialCredentialResponse, TrialSurveyRequest, TrialSurveyResponse
from app.auth import get_current_account
from app.services.trial import create_trial, get_trial_by_id, submit_trial_survey, check_trial_limit
from app.services.audit import log_audit_event
router = APIRouter(prefix="/api/trials", tags=["trials"])
@router.post("/claim", response_model=TrialClaimResponse, status_code=status.HTTP_201_CREATED)
async def claim_trial(request: TrialClaimRequest, session: AsyncSession = Depends(get_session), current_user: dict = Depends(get_current_account)):
    customer = current_user["customer"]
    if not customer: raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No customer profile found")
    if not request.disclaimer_accepted: raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Disclaimer must be accepted")
    if not await check_trial_limit(session, customer.phone): raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Daily trial limit reached")
    try:
        trial = await create_trial(session, phone=customer.phone, disclaimer_accepted=request.disclaimer_accepted)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    await log_audit_event(session, event_type="trial_claimed", phone=customer.phone, details={"trial_id": trial.id})
    result = await session.execute(select(BuncheCredential).where(BuncheCredential.id == trial.bunche_credential_id))
    credential = result.scalar_one_or_none()
    if not credential: raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create trial credential")
    return TrialClaimResponse(trial_id=trial.id, status=trial.status or "active",
        bunche_credential=TrialCredentialResponse(bun_username=credential.bun_username,
            upstream_proxy_ip=credential.upstream_proxy_ip or "0.0.0.0", upstream_proxy_port=credential.upstream_proxy_port, expires_at=credential.expires_at))
@router.post("/{trial_id}/survey", response_model=TrialSurveyResponse)
async def submit_survey(trial_id: int, request: TrialSurveyRequest, session: AsyncSession = Depends(get_session), current_user: dict = Depends(get_current_account)):
    customer = current_user["customer"]
    if not customer: raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No customer profile found")
    trial = await get_trial_by_id(session, trial_id)
    if not trial: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trial not found")
    if trial.phone != customer.phone: raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Trial does not belong to this user")
    try:
        survey = await submit_trial_survey(session, trial_id=trial_id, rating=request.rating, feedback=request.feedback, would_recommend=request.would_recommend)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    await log_audit_event(session, event_type="trial_survey_completed", phone=customer.phone, details={"trial_id": trial_id, "rating": request.rating})
    return TrialSurveyResponse(survey_id=str(survey.id), status=survey.status, reward_usd=trial.reward_usd)
