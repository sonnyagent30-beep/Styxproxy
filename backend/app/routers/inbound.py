"""Inbound email webhook router for Resend."""
import logging
import re
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import get_settings
from app.database import get_session
from app.models import SupportThread, SupportMessage, ProcessedWebhook
from app.services.email import send_email

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/api/v1/inbound", tags=["inbound"])

# Admin email to forward incoming messages to
ADMIN_EMAIL = "oyebiyiayomide30@gmail.com"
SUPPORT_EMAIL = "support@styxproxy.com"

# Spam detection patterns
SPAM_DOMAINS = [".ru", ".cn", ".su", ".by", ".kz", ".tk", ".ml", ".ga", ".cf", ".gq"]
SPAM_KEYWORDS = ["noreply", "no-reply", "bounce", "automated", "unsubscribe"]


def _extract_email_from_header(header: str) -> tuple[str, Optional[str]]:
    """Extract email and name from header like 'John Doe <john@example.com>'."""
    match = re.match(r"^(.+?)\s*<(.+?)>$", header.strip())
    if match:
        name = match.group(1).strip().strip('"')
        email = match.group(2).strip().lower()
        return email, name
    # No name, just email
    return header.strip().lower(), None


def _is_spam_sender(email: str) -> bool:
    """Check if sender looks like spam."""
    email_lower = email.lower()
    
    # Check for spam domains
    for domain in SPAM_DOMAINS:
        if email_lower.endswith(domain):
            return True
    
    # Check for spam keywords
    for keyword in SPAM_KEYWORDS:
        if keyword in email_lower:
            return True
    
    return False


class ResendInboundPayload(BaseModel):
    """Payload from Resend inbound email webhook."""
    type: str
    created_at: str
    data: dict


class InboundEmailData(BaseModel):
    """Parsed inbound email data."""
    email_id: str
    from_header: str
    to: list[str]
    subject: str
    message_id: str
    in_reply_to: Optional[str] = None
    references: Optional[str] = None
    text: Optional[str] = None
    html: Optional[str] = None


async def _find_thread_by_in_reply_to(
    session: AsyncSession,
    in_reply_to: str,
) -> Optional[SupportThread]:
    """Find thread by In-Reply-To header (Resend message ID)."""
    # Try to find by resend_last_message_id first (our sent messages)
    stmt = select(SupportThread).where(
        SupportThread.resend_last_message_id == in_reply_to
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def _find_thread_by_references(
    session: AsyncSession,
    references: str,
) -> Optional[SupportThread]:
    """Find thread by References header."""
    # The References header contains space-separated message IDs
    # The first one is the root, last is parent
    ref_ids = references.split()
    for ref_id in reversed(ref_ids):
        stmt = select(SupportThread).where(
            SupportThread.resend_last_message_id == ref_id.strip("<>")
        )
        result = await session.execute(stmt)
        thread = result.scalar_one_or_none()
        if thread:
            return thread
    return None


async def _create_new_thread(
    session: AsyncSession,
    from_email: str,
    from_name: Optional[str],
    subject: str,
    email_id: str,
) -> SupportThread:
    """Create a new support thread."""
    thread = SupportThread(
        customer_email=from_email,
        customer_name=from_name,
        subject=subject,
        status="open",
    )
    session.add(thread)
    await session.flush()  # Get the ID
    
    # Create initial inbound message
    message = SupportMessage(
        thread_id=thread.id,
        direction="inbound",
        from_email=from_email,
        to_email=SUPPORT_EMAIL,
        subject=subject,
        body_text=None,
        body_html=None,
        resend_id=email_id,
        in_reply_to=None,
        references=None,
    )
    session.add(message)
    
    return thread


async def _add_message_to_thread(
    session: AsyncSession,
    thread: SupportThread,
    from_email: str,
    to_email: str,
    subject: str,
    body_text: Optional[str],
    body_html: Optional[str],
    email_id: str,
    in_reply_to: Optional[str] = None,
    references: Optional[str] = None,
) -> SupportMessage:
    """Add a message to an existing thread."""
    message = SupportMessage(
        thread_id=thread.id,
        direction="inbound",
        from_email=from_email,
        to_email=to_email,
        subject=subject,
        body_text=body_text,
        body_html=body_html,
        resend_id=email_id,
        in_reply_to=in_reply_to,
        references=references,
    )
    session.add(message)
    
    # Update thread
    thread.last_message_at = datetime.utcnow()
    if thread.status == "closed":
        thread.status = "open"
    
    return message


async def _forward_to_admin(
    from_email: str,
    from_name: Optional[str],
    subject: str,
    body_text: Optional[str],
    body_html: Optional[str],
) -> bool:
    """Forward the inbound email to admin."""
    try:
        # Build a simple forward email
        forward_subject = f"[Support] {subject}"
        
        # Simple HTML wrapper for forwarded email
        forward_html = f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Forwarded Email</title></head>
<body style="font-family: -apple-system, sans-serif; padding: 20px;">
    <p><strong>From:</strong> {from_name or ''} &lt;{from_email}&gt;</p>
    <p><strong>Subject:</strong> {subject}</p>
    <hr>
    {body_html or '<pre>' + (body_text or '').replace('<', '&lt;').replace('>', '&gt;') + '</pre>'}
</body>
</html>
"""
        
        result = await send_email(
            to=ADMIN_EMAIL,
            subject=forward_subject,
            html=forward_html,
            text=body_text,
        )
        
        if result.success:
            logger.info(f"Forwarded inbound email to admin: {ADMIN_EMAIL}")
            return True
        else:
            logger.error(f"Failed to forward email to admin: {result.error}")
            return False
    except Exception as e:
        logger.error(f"Error forwarding to admin: {e}")
        return False


@router.post("/resend")
async def receive_resend_webhook(
    request: Request,
    payload: ResendInboundPayload,
    session: AsyncSession = Depends(get_session),
):
    """
    Receive inbound email webhook from Resend.
    
    Resend sends this when someone emails support@styxproxy.com
    """
    # Validate event type
    if payload.type != "email.received":
        logger.warning(f"Ignoring non-email.received event: {payload.type}")
        return {"status": "ignored", "reason": "not an inbound email"}
    
    data = payload.data
    
    # Parse the email data
    email_id = data.get("email_id", "")
    from_header = data.get("from", "")
    to_list = data.get("to", [])
    subject = data.get("subject", "(No Subject)")
    message_id = data.get("message_id", "")
    in_reply_to = data.get("in_reply_to")
    references = data.get("references")
    text = data.get("text")
    html = data.get("html")
    
    # Extract email and name from From header
    from_email, from_name = _extract_email_from_header(from_header)
    
    # Idempotency: check if already processed
    existing = await session.execute(
        select(ProcessedWebhook).where(
            ProcessedWebhook.webhook_id == email_id
        )
    )
    if existing.scalar_one_or_none():
        logger.info(f"Email already processed: {email_id}")
        return {"status": "already_processed", "email_id": email_id}
    
    # Spam check
    if _is_spam_sender(from_email):
        logger.warning(f"Blocking spam email from: {from_email}")
        # Still record it as processed to avoid reprocessing
        processed = ProcessedWebhook(
            webhook_id=email_id,
            provider="resend",
            event_type="email.received",
            response_sent=True,
            extra_data={"spam": True, "from": from_email},
        )
        session.add(processed)
        await session.commit()
        return {"status": "blocked_spam", "email_id": email_id}
    
    # Find or create thread
    thread = None
    if in_reply_to:
        thread = await _find_thread_by_in_reply_to(session, in_reply_to)
    
    if not thread and references:
        thread = await _find_thread_by_references(session, references)
    
    if thread:
        # Add to existing thread
        message = await _add_message_to_thread(
            session=session,
            thread=thread,
            from_email=from_email,
            to_email=SUPPORT_EMAIL,
            subject=subject,
            body_text=text,
            body_html=html,
            email_id=email_id,
            in_reply_to=in_reply_to,
            references=references,
        )
        logger.info(f"Added reply to thread {thread.id}")
    else:
        # New conversation
        thread = await _create_new_thread(
            session=session,
            from_email=from_email,
            from_name=from_name,
            subject=subject,
            email_id=email_id,
        )
        # Update the message with body
        message = await _add_message_to_thread(
            session=session,
            thread=thread,
            from_email=from_email,
            to_email=SUPPORT_EMAIL,
            subject=subject,
            body_text=text,
            body_html=html,
            email_id=email_id,
            in_reply_to=in_reply_to,
            references=references,
        )
        logger.info(f"Created new thread {thread.id}")
    
    # Record as processed (idempotency)
    processed = ProcessedWebhook(
        webhook_id=email_id,
        provider="resend",
        event_type="email.received",
        response_sent=True,
        extra_data={
            "thread_id": str(thread.id),
            "from": from_email,
            "subject": subject,
        },
    )
    session.add(processed)
    
    # Forward to admin (don't await - send in background)
    # Note: In production, consider using a task queue
    await _forward_to_admin(
        from_email=from_email,
        from_name=from_name,
        subject=subject,
        body_text=text,
        body_html=html,
    )
    
    await session.commit()
    
    return {
        "status": "received",
        "email_id": email_id,
        "thread_id": str(thread.id),
    }


# Import Depends at module level
from fastapi import Depends
