"""Admin support threads router - manage customer support conversations."""
import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.database import get_session
from app.auth import admin_only
from app.models import SupportThread, SupportMessage
from app.services.email import send_support_reply_email, send_email

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin/support", tags=["admin-support"])


# =============================================================================
# Pydantic Schemas
# =============================================================================

class SupportMessageResponse(BaseModel):
    """Support message response."""
    id: str
    thread_id: str
    direction: str
    from_email: str
    to_email: str
    subject: str
    body_text: Optional[str]
    body_html: Optional[str]
    resend_id: Optional[str]
    in_reply_to: Optional[str]
    references: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class SupportThreadResponse(BaseModel):
    """Support thread response."""
    id: str
    customer_email: str
    customer_name: Optional[str]
    subject: str
    status: str
    order_id: Optional[str]
    resend_last_message_id: Optional[str]
    last_message_at: datetime
    created_at: datetime
    messages: list[SupportMessageResponse] = []

    class Config:
        from_attributes = True


class SupportThreadListResponse(BaseModel):
    """List of support threads."""
    threads: list[SupportThreadResponse]
    pagination: dict


class SupportReplyRequest(BaseModel):
    """Request to reply to a support thread."""
    reply_html: str
    admin_name: str = "Dannion"


class SupportThreadCloseRequest(BaseModel):
    """Request to close a support thread."""
    reason: Optional[str] = None


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/threads", response_model=SupportThreadListResponse, dependencies=[Depends(admin_only)])
async def list_support_threads(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
    session: AsyncSession = Depends(get_session),
):
    """
    List all support threads with pagination.
    
    Args:
        page: Page number (1-indexed)
        limit: Items per page
        status_filter: Filter by status (open, replied, closed)
    """
    conditions = []
    if status_filter:
        conditions.append(SupportThread.status == status_filter)
    
    # Count total
    count_stmt = select(func.count()).select_from(SupportThread)
    if conditions:
        count_stmt = count_stmt.where(and_(*conditions))
    total = (await session.execute(count_stmt)).scalar() or 0
    
    # Get paginated results
    offset = (page - 1) * limit
    stmt = (
        select(SupportThread)
        .order_by(SupportThread.last_message_at.desc())
        .offset(offset)
        .limit(limit)
    )
    if conditions:
        stmt = stmt.where(and_(*conditions))
    
    threads = (await session.execute(stmt)).scalars().all()
    
    return SupportThreadListResponse(
        threads=[
            SupportThreadResponse(
                id=str(t.id),
                customer_email=t.customer_email,
                customer_name=t.customer_name,
                subject=t.subject,
                status=t.status,
                order_id=t.order_id,
                resend_last_message_id=t.resend_last_message_id,
                last_message_at=t.last_message_at,
                created_at=t.created_at,
            )
            for t in threads
        ],
        pagination={
            "page": page,
            "limit": limit,
            "total_items": total,
            "total_pages": (total + limit - 1) // limit,
            "has_next": page * limit < total,
            "has_prev": page > 1,
        },
    )


@router.get("/threads/{thread_id}", response_model=SupportThreadResponse, dependencies=[Depends(admin_only)])
async def get_support_thread(
    thread_id: UUID,
    include_messages: bool = Query(True),
    session: AsyncSession = Depends(get_session),
):
    """
    Get a specific support thread with all messages.
    """
    stmt = select(SupportThread).where(SupportThread.id == thread_id)
    thread = (await session.execute(stmt)).scalar_one_or_none()
    
    if not thread:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Support thread not found",
        )
    
    messages = []
    if include_messages:
        msg_stmt = (
            select(SupportMessage)
            .where(SupportMessage.thread_id == thread_id)
            .order_by(SupportMessage.created_at.asc())
        )
        messages = (await session.execute(msg_stmt)).scalars().all()
    
    return SupportThreadResponse(
        id=str(thread.id),
        customer_email=thread.customer_email,
        customer_name=thread.customer_name,
        subject=thread.subject,
        status=thread.status,
        order_id=thread.order_id,
        resend_last_message_id=thread.resend_last_message_id,
        last_message_at=thread.last_message_at,
        created_at=thread.created_at,
        messages=[
            SupportMessageResponse(
                id=str(m.id),
                thread_id=str(m.thread_id),
                direction=m.direction,
                from_email=m.from_email,
                to_email=m.to_email,
                subject=m.subject,
                body_text=m.body_text,
                body_html=m.body_html,
                resend_id=m.resend_id,
                in_reply_to=m.in_reply_to,
                references=m.references,
                created_at=m.created_at,
            )
            for m in messages
        ],
    )


@router.post("/threads/{thread_id}/reply", dependencies=[Depends(admin_only)])
async def reply_to_support_thread(
    thread_id: UUID,
    request: SupportReplyRequest,
    session: AsyncSession = Depends(get_session),
):
    """
    Reply to a support thread.
    
    Sends an email to the customer from support@styxproxy.com with proper
    threading headers. The reply is also saved to the database.
    """
    # Get the thread
    stmt = select(SupportThread).where(SupportThread.id == thread_id)
    thread = (await session.execute(stmt)).scalar_one_or_none()
    
    if not thread:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Support thread not found",
        )
    
    if thread.status == "closed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot reply to a closed thread",
        )
    
    # Get the last outbound message for threading headers
    last_outbound_stmt = (
        select(SupportMessage)
        .where(
            and_(
                SupportMessage.thread_id == thread_id,
                SupportMessage.direction == "outbound",
            )
        )
        .order_by(SupportMessage.created_at.desc())
    )
    last_outbound = (await session.execute(last_outbound_stmt)).scalar_one_or_none()
    
    # Build threading headers
    in_reply_to = thread.resend_last_message_id
    references = in_reply_to
    if last_outbound and last_outbound.resend_id:
        # Add to references if there's a previous outbound
        if references:
            references = f"{references} {last_outbound.resend_id}"
        else:
            references = last_outbound.resend_id
    
    # Send the email
    customer_email = thread.customer_email
    customer_name = thread.customer_name or "Customer"
    
    result = await send_support_reply_email(
        customer_email=customer_email,
        customer_name=customer_name,
        original_subject=thread.subject,
        reply_body_html=request.reply_html,
        admin_name=request.admin_name,
        in_reply_to=in_reply_to,
        references=references,
    )
    
    if not result.success:
        logger.error(f"Failed to send reply email: {result.error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send email: {result.error}",
        )
    
    # Save the outbound message to DB
    outbound_message = SupportMessage(
        thread_id=thread.id,
        direction="outbound",
        from_email="support@styxproxy.com",
        to_email=customer_email,
        subject=f"Re: {thread.subject}",
        body_text=None,
        body_html=request.reply_html,
        resend_id=result.message_id,
        in_reply_to=in_reply_to,
        references=references,
    )
    session.add(outbound_message)
    
    # Update thread
    thread.last_message_at = datetime.utcnow()
    thread.status = "replied"
    thread.resend_last_message_id = result.message_id
    
    await session.commit()
    
    return {
        "status": "sent",
        "message_id": result.message_id,
        "thread_id": str(thread.id),
    }


@router.post("/threads/{thread_id}/close", dependencies=[Depends(admin_only)])
async def close_support_thread(
    thread_id: UUID,
    request: SupportThreadCloseRequest = None,
    session: AsyncSession = Depends(get_session),
):
    """
    Close a support thread.
    """
    stmt = select(SupportThread).where(SupportThread.id == thread_id)
    thread = (await session.execute(stmt)).scalar_one_or_none()
    
    if not thread:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Support thread not found",
        )
    
    thread.status = "closed"
    thread.last_message_at = datetime.utcnow()
    
    await session.commit()
    
    return {
        "status": "closed",
        "thread_id": str(thread.id),
    }


@router.post("/threads/{thread_id}/reopen", dependencies=[Depends(admin_only)])
async def reopen_support_thread(
    thread_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    """
    Reopen a closed support thread.
    """
    stmt = select(SupportThread).where(SupportThread.id == thread_id)
    thread = (await session.execute(stmt)).scalar_one_or_none()
    
    if not thread:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Support thread not found",
        )
    
    thread.status = "open"
    thread.last_message_at = datetime.utcnow()
    
    await session.commit()
    
    return {
        "status": "reopened",
        "thread_id": str(thread.id),
    }
