"""Trial service for free trial management."""
import random, string, uuid
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models import FreeTrial, PendingTrialSurvey
from app.services.credential import create_credential
TRIAL_DURATION_HOURS = 2
MAX_TRIALS_PER_DAY = 3
SURVEY_REWARD_USD = 1.00
async def check_trial_limit(db_session: AsyncSession, phone: str) -> bool:
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    count = (await db_session.execute(select(func.count()).select_from(FreeTrial).where(FreeTrial.phone == phone, FreeTrial.trial_date >= today_start))).scalar() or 0
    return count < MAX_TRIALS_PER_DAY
async def create_trial(db_session: AsyncSession, phone: str, disclaimer_accepted: bool = False) -> FreeTrial:
    if not await check_trial_limit(db_session, phone):
        raise ValueError("Daily trial limit reached")
    from app.models import BuncheCredential
    from app.auth import get_password_hash
    expires_at = datetime.utcnow() + timedelta(hours=TRIAL_DURATION_HOURS)
    credential = BuncheCredential(bun_username=f"trial_{''.join(random.choices(string.ascii_lowercase, k=8))}", password_hash=get_password_hash("".join(random.choices(string.ascii_letters + string.digits, k=16))), customer_phone=phone, pool_type="free_trial", upstream_proxy_ip="192.168.1.1", upstream_proxy_port=1080, dante_port=random.randint(9000, 9999), status="active", expires_at=expires_at)
    db_session.add(credential)
    await db_session.flush()
    trial = FreeTrial(phone=phone, bunche_credential_id=credential.id, status="active", disclaimer_accepted=disclaimer_accepted)
    db_session.add(trial)
    await db_session.commit()
    await db_session.refresh(trial)
    return trial
async def get_trial_by_id(db_session: AsyncSession, trial_id: int) -> Optional[FreeTrial]:
    return (await db_session.execute(select(FreeTrial).where(FreeTrial.id == trial_id))).scalar_one_or_none()
async def complete_trial(db_session: AsyncSession, trial_id: int, status: str = "expired") -> Optional[FreeTrial]:
    trial = await get_trial_by_id(db_session, trial_id)
    if trial:
        trial.status = status
        if trial.bunche_credential_id:
            cred = (await db_session.execute(select(BuncheCredential).where(BuncheCredential.id == trial.bunche_credential_id))).scalar_one_or_none()
            if cred:
                cred.status = "expired"
        await db_session.commit()
    return trial
async def create_trial_survey(db_session: AsyncSession, trial_id: int, customer_id: uuid.UUID) -> PendingTrialSurvey:
    survey_token = str(uuid.uuid4())
    questions = {"rating": "How would you rate your experience?", "feedback": "Any feedback for improvement?", "would_recommend": "Would you recommend our service?"}
    survey = PendingTrialSurvey(free_trial_id=trial_id, customer_id=customer_id, survey_token=survey_token, questions=questions, status="pending")
    db_session.add(survey)
    await db_session.commit()
    await db_session.refresh(survey)
    return survey
async def submit_trial_survey(db_session: AsyncSession, trial_id: int, rating: int, feedback: str, would_recommend: bool) -> PendingTrialSurvey:
    trial = await get_trial_by_id(db_session, trial_id)
    if not trial:
        raise ValueError("Trial not found")
    survey = (await db_session.execute(select(PendingTrialSurvey).where(PendingTrialSurvey.free_trial_id == trial_id, PendingTrialSurvey.status == "pending"))).scalar_one_or_none()
    if not survey:
        raise ValueError("Survey not found")
    survey.responses = {"rating": rating, "feedback": feedback, "would_recommend": would_recommend}
    survey.status = "completed"
    survey.completed_at = datetime.utcnow()
    trial.reward_usd = SURVEY_REWARD_USD
    await db_session.commit()
    await db_session.refresh(survey)
    return survey
async def get_trials_today_count(db_session: AsyncSession) -> int:
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    return (await db_session.execute(select(func.count()).select_from(FreeTrial).where(FreeTrial.trial_date >= today_start))).scalar() or 0
