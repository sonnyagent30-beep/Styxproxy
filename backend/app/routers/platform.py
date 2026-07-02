"""Platform accounts router."""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_session
from app.models import Customer, PlatformAccount, MergeRequest
from app.schemas import PlatformRegisterRequest, PlatformRegisterResponse, PlatformMeResponse, CustomerBrief, PlatformAccountResponse, MergeRequestRequest, MergeRequestResponse
from app.auth import get_current_account
from app.services.audit import log_audit_event
router = APIRouter(prefix="/api/platform", tags=["platform"])
@router.post("/register", response_model=PlatformRegisterResponse, status_code=status.HTTP_201_CREATED)
async def register_platform(request: PlatformRegisterRequest, session: AsyncSession = Depends(get_session), current_user: dict = Depends(get_current_account)):
    platform_account = PlatformAccount(customer_id=current_user["customer"].id if current_user["customer"] else None,
        platform=request.platform.value, platform_user_id=request.platform_user_id, metadata=request.metadata, is_primary=True)
    session.add(platform_account)
    await session.commit()
    await session.refresh(platform_account)
    await log_audit_event(session, event_type="platform_registered",
        phone=current_user["customer"].phone if current_user["customer"] else None,
        details={"platform": request.platform.value, "platform_user_id": request.platform_user_id})
    return PlatformRegisterResponse.model_validate(platform_account)
@router.get("/me", response_model=PlatformMeResponse)
async def get_my_account(session: AsyncSession = Depends(get_session), current_user: dict = Depends(get_current_account)):
    customer = current_user["customer"]
    platform_account = current_user["platform_account"]
    if not customer:
        return PlatformMeResponse(customer=None, accounts=[PlatformAccountResponse.model_validate(platform_account)])
    stmt = select(PlatformAccount).where(PlatformAccount.customer_id == customer.id)
    result = await session.execute(stmt)
    accounts = result.scalars().all()
    return PlatformMeResponse(customer=CustomerBrief(id=customer.id, phone=customer.phone, name=customer.name),
        accounts=[PlatformAccountResponse.model_validate(acc) for acc in accounts])
@router.post("/merge", response_model=MergeRequestResponse, status_code=status.HTTP_201_CREATED)
async def merge_accounts(request: MergeRequestRequest, session: AsyncSession = Depends(get_session), current_user: dict = Depends(get_current_account)):
    customer = current_user["customer"]
    if not customer: raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No customer profile found")
    stmt = select(PlatformAccount).where(PlatformAccount.id == request.source_account_id, PlatformAccount.customer_id == customer.id)
    result = await session.execute(stmt)
    source_account = result.scalar_one_or_none()
    if not source_account: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source account not found")
    stmt = select(PlatformAccount).where(PlatformAccount.id == request.target_account_id, PlatformAccount.customer_id == customer.id)
    result = await session.execute(stmt)
    target_account = result.scalar_one_or_none()
    if not target_account: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target account not found")
    merge_request = MergeRequest(source_account_id=request.source_account_id, target_account_id=request.target_account_id, requested_by=customer.id, status="pending")
    session.add(merge_request)
    await session.commit()
    await session.refresh(merge_request)
    return MergeRequestResponse.model_validate(merge_request)
