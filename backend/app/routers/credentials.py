"""Credentials router."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_session
from app.models import BuncheCredential
from app.schemas import CredentialsListResponse, CredentialResponse
from app.auth import get_current_account
from app.services.credential import get_active_credentials_by_phone

router = APIRouter(prefix="/api/credentials", tags=["credentials"])


@router.get("", response_model=CredentialsListResponse)
async def list_credentials(
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_account),
):
    customer = current_user["customer"]
    if not customer:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No customer profile found")
    credentials = await get_active_credentials_by_phone(session, customer.phone)
    return CredentialsListResponse(credentials=[CredentialResponse.model_validate(cred) for cred in credentials])


@router.get("/{order_id}", response_model=CredentialResponse)
async def get_credential_by_order(
    order_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_account),
):
    customer = current_user["customer"]
    if not customer:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No customer profile found")
    stmt = select(BuncheCredential).where(
        BuncheCredential.order_id == order_id,
        BuncheCredential.customer_phone == customer.phone,
    )
    result = await session.execute(stmt)
    credential = result.scalar_one_or_none()
    if not credential:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Credential not found")
    return CredentialResponse.model_validate(credential)
