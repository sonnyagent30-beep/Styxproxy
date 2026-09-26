"""Public support ticket router — customer-facing ticket creation and lookup."""
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.limiter import limiter
from app.models import SupportMessage, SupportThread
from app.services.email import EmailRecipient, _send_via_resend

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/support", tags=["support"])


# =============================================================================
# Pydantic Schemas
# =============================================================================


class CreateTicketRequest(BaseModel):
    """Request to create a support ticket."""

    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    subject: str = Field(..., min_length=1, max_length=500)
    message: str = Field(..., min_length=1, max_length=5000)
    order_id: Optional[str] = Field(None, max_length=50)


class TicketResponse(BaseModel):
    """Ticket creation response."""

    ticket_id: str
    status: str
    message: str


class TicketLookupResponse(BaseModel):
    """Response for ticket lookup by email."""

    tickets: list[dict]


# =============================================================================
# Endpoints
# =============================================================================


@router.post(
    "/tickets",
    response_model=TicketResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("5/hour")
async def create_ticket(
    request: Request,
    body: CreateTicketRequest,
    session: AsyncSession = Depends(get_session),
):
    """Create a new support ticket.

    Creates a SupportThread and initial SupportMessage, then sends a
    confirmation email to the customer.
    """
    # Create the support thread
    thread = SupportThread(
        customer_email=str(body.email),
        customer_name=body.name,
        subject=body.subject,
        status="open",
        order_id=body.order_id,
    )
    session.add(thread)
    await session.flush()  # Get thread.id without committing

    # Create the initial inbound message
    message = SupportMessage(
        thread_id=thread.id,
        direction="inbound",
        from_email=str(body.email),
        to_email="support@styxproxy.com",
        subject=body.subject,
        body_text=body.message,
        body_html=None,
    )
    session.add(message)

    await session.commit()

    logger.info(
        "Support ticket created",
        extra={
            "ticket_id": str(thread.id),
            "email": str(body.email),
            "subject": body.subject,
        },
    )

    # Send confirmation email (best-effort — don't fail the request if email fails)
    try:
        ticket_short = str(thread.id)[:8]
        confirmation_html = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>Ticket Confirmation</title></head>
<body style="font-family: sans-serif; background: #0f0f0f; color: #f5f5f5; padding: 40px;">
    <div style="max-width: 500px; margin: 0 auto;">
        <div style="height: 4px; background: #00D060; border-radius: 2px; margin-bottom: 24px;"></div>
        <h1 style="color: #00D060; font-size: 22px; margin-bottom: 12px;">Ticket Received</h1>
        <p style="color: #d1d5db; margin-bottom: 16px;">Hi {body.name},</p>
        <p style="color: #9ca3af; margin-bottom: 16px;">We have received your support request and will get back to you within 24 hours.</p>
        <div style="background: #1a1a2e; border: 1px solid #374151; border-radius: 8px; padding: 16px; margin: 16px 0;">
            <p style="color: #00D060; margin: 0 0 8px 0; font-size: 13px; font-weight: bold;">TICKET ID</p>
            <p style="color: #f5f5f5; margin: 0; font-size: 16px; font-family: monospace;">#{ticket_short}</p>
            <p style="color: #6b7280; margin: 8px 0 0 0; font-size: 12px;">{body.subject}</p>
        </div>
        <p style="color: #6b7280; font-size: 12px;">A confirmation has been sent to {body.email}.</p>
    </div>
</body>
</html>"""
        await _send_via_resend(
            recipient=EmailRecipient(email=str(body.email), name=body.name),
            subject=f"Ticket Received: {body.subject}",
            html=confirmation_html,
            text=f"Hi {body.name}, we have received your support request. Ticket ID: #{ticket_short}. We will respond within 24 hours.",
        )
    except Exception as exc:
        logger.warning(f"Failed to send ticket confirmation email: {exc}")
        # Don't fail the request — ticket is already created

    return TicketResponse(
        ticket_id=str(thread.id),
        status="open",
        message="Ticket created successfully. Check your email for confirmation.",
    )


@router.get("/tickets/lookup", response_model=TicketLookupResponse)
async def lookup_tickets(
    email: EmailStr,
    session: AsyncSession = Depends(get_session),
):
    """Look up support tickets by customer email."""
    stmt = (
        select(SupportThread)
        .where(SupportThread.customer_email == str(email))
        .order_by(SupportThread.created_at.desc())
        .limit(50)
    )
    threads = (await session.execute(stmt)).scalars().all()

    return TicketLookupResponse(
        tickets=[
            {
                "id": str(t.id),
                "subject": t.subject,
                "status": t.status,
                "order_id": t.order_id,
                "last_message_at": t.last_message_at.isoformat() if t.last_message_at else None,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in threads
        ]
    )
