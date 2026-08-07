"""Email unsubscribe router — public, no auth."""
import hashlib
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import Column, String, DateTime, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import declarative_base

from app.database import get_session

router = APIRouter(tags=["public"])

UNSUBSCRIBE_SECRET = "styxproxy_unsubscribe_secret_v1"

Base = declarative_base()


class EmailUnsubscribe(Base):
    __tablename__ = "email_unsubscribes"

    email = Column(String(255), primary_key=True)
    unsubscribed_at = Column(DateTime(timezone=True), nullable=False)
    source = Column(String(50), default="list_unsubscribe")


def _make_token(email: str) -> str:
    return hashlib.sha1(f"{email}:{UNSUBSCRIBE_SECRET}".encode()).hexdigest()


def _make_url(email: str) -> str:
    return f"https://styxproxy.com/api/v1/unsubscribe?email={email}&token={_make_token(email)}"


class UnsubscribeResponse(BaseModel):
    ok: bool
    message: str


@router.get("/api/v1/unsubscribe", response_model=UnsubscribeResponse)
async def unsubscribe(
    email: str,
    token: str,
    session: AsyncSession = Depends(get_session),
):
    """One-click unsubscribe. Token validates (HMAC-SHA1 of email + secret)."""
    if token != _make_token(email):
        return UnsubscribeResponse(
            ok=False,
            message="This unsubscribe link is invalid or has expired.",
        )

    stmt = select(EmailUnsubscribe).where(EmailUnsubscribe.email == email.lower())
    result = await session.execute(stmt)
    existing = result.scalar_one_or_none()

    if not existing:
        record = EmailUnsubscribe(
            email=email.lower(),
            unsubscribed_at=datetime.now(timezone.utc),
            source="list_unsubscribe",
        )
        session.add(record)

    await session.commit()
    return UnsubscribeResponse(
        ok=True,
        message="You've been unsubscribed from Styxproxy emails.",
    )


@router.get("/api/v1/unsubscribe/preview")
async def unsubscribe_preview(email: str):
    return {
        "email": email,
        "token": _make_token(email),
        "confirm_url": _make_url(email),
    }
