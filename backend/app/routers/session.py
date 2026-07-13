"""Anonymous device session management.

Website users are 100% anonymous — no login, no name, no email.
We track them via a device_id UUID stored in localStorage on the client.
This lets us:
1. Prevent duplicate in-flight payments (same device can't start 2 payments in 5min)
2. Let customers find their past orders without login (orders tied to device_id)
3. Issue JWT cookies so the rest of the API works (no auth code changes)

The device_id is NOT PII — just a UUID tied to one browser.
Same browser = same device_id. Different browser = different device_id.
Customers who clear browser data lose their order history (acceptable trade-off for privacy).
"""
from datetime import datetime, timedelta, timezone
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import create_access_token, settings
from app.database import get_session
from app.models import PlatformAccount

router = APIRouter(prefix="/api/session", tags=["session"])

# Anonymous sessions expire in 30 days — long enough for a customer to come back
ANONYMOUS_SESSION_DAYS = 30


class InitSessionRequest(BaseModel):
    device_id: str = Field(..., min_length=8, max_length=64)


class InitSessionResponse(BaseModel):
    session_id: str
    expires_in_days: int
    device_id: str


@router.post("/init", response_model=InitSessionResponse)
async def init_session(
    payload: InitSessionRequest,
    response: Response,
    session: AsyncSession = Depends(get_session),
):
    """Initialize an anonymous device session.

    Called by the frontend on first visit (and on every page load to refresh the cookie).
    - Looks up PlatformAccount by (platform='web', platform_user_id=device_id)
    - Creates one if missing — anonymous, no Customer.name
    - Issues JWT cookie scoped to that PlatformAccount
    """
    device_id = payload.device_id.strip()
    if not device_id or len(device_id) < 8:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid device_id")

    # Look up or create the anonymous PlatformAccount
    stmt = select(PlatformAccount).where(
        PlatformAccount.platform == "web",
        PlatformAccount.platform_user_id == device_id,
    )
    result = await session.execute(stmt)
    platform_account = result.scalar_one_or_none()

    if platform_account is None:
        platform_account = PlatformAccount(
            customer_id=None,  # anonymous — no customer profile
            platform="web",
            platform_user_id=device_id,
            device_id=device_id,
            is_primary=True,
        )
        session.add(platform_account)
        await session.commit()
        await session.refresh(platform_account)

    # Issue JWT — same format as authenticated users so all existing endpoints work
    access_token = create_access_token(
        sub=str(platform_account.id),
        platform="web",
        phone="",  # no phone for anonymous
        expires_delta=timedelta(days=ANONYMOUS_SESSION_DAYS),
    )

    # Set httpOnly cookie — frontend can't read it, only backend uses it
    response.set_cookie(
        key="styxproxy_session",
        value=access_token,
        max_age=ANONYMOUS_SESSION_DAYS * 24 * 60 * 60,
        httponly=True,
        secure=True,  # require HTTPS in production
        samesite="lax",
        path="/",
    )

    return InitSessionResponse(
        session_id=str(platform_account.id),
        expires_in_days=ANONYMOUS_SESSION_DAYS,
        device_id=device_id,
    )


@router.post("/refresh")
async def refresh_session(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
):
    """Refresh the JWT cookie if it exists. Extends the session."""
    token = request.cookies.get("styxproxy_session")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No active session")

    # Decode the existing token to get the platform_account_id
    from app.auth import decode_access_token
    payload = decode_access_token(token)
    platform_account_id = payload.get("sub")
    if not platform_account_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    # Issue new token
    new_token = create_access_token(
        sub=platform_account_id,
        platform="web",
        phone="",
        expires_delta=timedelta(days=ANONYMOUS_SESSION_DAYS),
    )
    response.set_cookie(
        key="styxproxy_session",
        value=new_token,
        max_age=ANONYMOUS_SESSION_DAYS * 24 * 60 * 60,
        httponly=True,
        secure=True,
        samesite="lax",
        path="/",
    )
    return {"status": "refreshed", "expires_in_days": ANONYMOUS_SESSION_DAYS}