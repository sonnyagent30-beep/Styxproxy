"""Inbound email webhook router for Resend."""

import asyncio
import logging
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_session
from app.models import ProcessedWebhook, SupportMessage, SupportThread
from app.services.email import send_email
from app.utils.html_sanitize import sanitize_html
import redis.asyncio as redis

logger = logging.getLogger(__name__)

# Keep strong references to in-flight background tasks so they are not
# garbage-collected mid-execution. Without this, asyncio.create_task can
# silently drop the forward — the exact "fire and hope" pattern we removed
# from the escalation path.
_inflight_tasks: set[asyncio.Task] = set()

# ── Rate limiting ────────────────────────────────────────────────────────────────
RATE_LIMIT_WINDOW = 3600   # 1 hour
RATE_LIMIT_MAX   = 5      # 5 messages per sender per hour
_redis_client: redis.Redis | None = None

async def _get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        url = getattr(get_settings(), "redis_url", "redis://:styxproxy_redis_2026@127.0.0.1:6379/0")
        _redis_client = redis.from_url(url, decode_responses=True)
    return _redis_client

async def _check_rate_limit(sender_email: str) -> tuple[bool, int]:
    """5 msgs/hr per sender via Redis sliding window. Returns (allowed, remaining)."""
    try:
        client = await _get_redis()
        key    = f"inbound:rate:{sender_email}"
        now    = time.time()
        window = now - RATE_LIMIT_WINDOW

        pipe = client.pipeline()
        pipe.zremrangebyscore(key, 0, window)
        pipe.zcard(key)
        results = await pipe.execute()
        count = results[1]

        if count >= RATE_LIMIT_MAX:
            return False, 0

        await client.zadd(key, {str(now): now})
        await client.expire(key, RATE_LIMIT_WINDOW + 60)
        return True, max(0, RATE_LIMIT_MAX - count - 1)

    except Exception as e:
        logger.warning(f"Redis rate limit check failed (allowing): {e}")
        return True, RATE_LIMIT_MAX   # fail open

# ── MIME validation ─────────────────────────────────────────────────────────────
MAX_EMAIL_SIZE   = 10 * 1024 * 1024   # 10 MB
BLOCKED_MIME_TYPES = {
    "application/octet-stream", "application/x-executable",
    "application/x-msdownload", "application/zip",
    "application/x-zip-compressed", "application/javascript",
    "text/javascript",
}

def _validate_mime(request) -> tuple[bool, str]:
    """Reject oversized or dangerous Content-Types."""
    cl = request.headers.get("content-length")
    if cl:
        try:
            if int(cl) > MAX_EMAIL_SIZE:
                return False, f"Payload too large (>{MAX_EMAIL_SIZE // 1024//1024}MB)"
        except ValueError:
            pass

    ct = request.headers.get("content-type", "").lower()
    if ct in BLOCKED_MIME_TYPES:
        return False, f"Blocked Content-Type: {ct}"

    return True, ""

# ── Svix signature verification ────────────────────────────────────────────────
SVIX_TIMESTAMP_TOLERANCE = 300  # 5 minutes

def _verify_svix_signature(request: Request, body: bytes) -> bool:
    """
    Verify the Svix webhook signature from Resend.
    
    Resend signs webhooks with HMAC-SHA256. The signature is computed as:
        HMAC-SHA256(secret, f"{timestamp}.{body}")
    
    Headers expected:
        svix-id: unique message ID
        svix-timestamp: Unix timestamp
        svix-signature: space-separated base64 signatures (e.g., "v1,base64sig")
    
    The secret from the Resend dashboard starts with "whsec_" — we strip that prefix.
    
    Returns True if the signature is valid, False otherwise.
    """
    import hmac
    import hashlib
    import base64
    
    svix_id = request.headers.get("svix-id")
    svix_timestamp = request.headers.get("svix-timestamp")
    svix_signature = request.headers.get("svix-signature")
    
    if not svix_id or not svix_timestamp or not svix_signature:
        logger.warning("Missing Svix signature headers")
        return False
    
    # Check timestamp tolerance (reject replays)
    try:
        ts = int(svix_timestamp)
        now = int(time.time())
        if abs(now - ts) > SVIX_TIMESTAMP_TOLERANCE:
            logger.warning(f"Svix timestamp too old: {ts} (now={now}, diff={now - ts}s)")
            return False
    except (ValueError, TypeError):
        logger.warning(f"Invalid Svix timestamp: {svix_timestamp}")
        return False
    
    # Get the signing secret (strip whsec_ prefix)
    secret = settings.resend_webhook_secret
    if not secret:
        logger.error("RESEND_WEBHOOK_SECRET not configured — rejecting webhook")
        return False
    
    if secret.startswith("whsec_"):
        secret = secret[6:]
    
    # Svix: the signing key is the BASE64-DECODED bytes after "whsec_",
    # and the signed content is "{msg_id}.{timestamp}.{body}" — the message id
    # is REQUIRED. Omitting it rejects every real webhook.
    # Verified against svix.webhooks.Webhook.sign(msg_id, timestamp, data):
    # the official implementation signs exactly this three-part string.
    try:
        signing_key = base64.b64decode(secret)
    except Exception:
        logger.error("RESEND_WEBHOOK_SECRET is not valid base64 after whsec_ prefix")
        return False
    
    signed_content = f"{svix_id}.{svix_timestamp}.".encode() + body
    expected_sig = base64.b64encode(
        hmac.new(signing_key, signed_content, hashlib.sha256).digest()
    ).decode()
    
    # The svix-signature header contains space-separated signatures like "v1,base64sig"
    # We check if our expected signature is among them
    signatures = svix_signature.split()
    for sig in signatures:
        # Each signature is in format "v1,base64sig"
        if sig.startswith("v1,"):
            actual_sig = sig[3:]
            if hmac.compare_digest(expected_sig, actual_sig):
                return True
    
    logger.warning("Svix signature verification failed")
    return False


# ── Auto-close stale threads ───────────────────────────────────────────────────
AUTO_CLOSE_DAYS = 14

async def _auto_close_stale_threads(session) -> int:
    """Close open threads with no customer reply in 14 days."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=AUTO_CLOSE_DAYS)

    subq = (
        select(SupportMessage.thread_id, SupportMessage.direction, SupportMessage.created_at)
        .where(
            SupportMessage.thread_id.in_(
                select(SupportThread.id).where(SupportThread.status == "open")
            )
        )
        .order_by(SupportMessage.thread_id, SupportMessage.created_at.desc())
        .distinct(SupportMessage.thread_id)
    ).subquery()

    stmt = (
        select(SupportThread)
        .join(subq, SupportThread.id == subq.c.thread_id)
        .where(
            and_(
                SupportThread.status == "open",
                subq.c.direction == "outbound",
                subq.c.created_at < cutoff,
            )
        )
    )
    result = await session.execute(stmt)
    stale = result.scalars().all()

    for t in stale:
        t.status = "closed"

    if stale:
        await session.commit()
        logger.info(f"Auto-closed {len(stale)} stale support threads")

    return len(stale)
settings = get_settings()


async def _forward_to_dannion(
    from_email: str,
    from_name: Optional[str],
    subject: str,
    body_text: Optional[str],
    body_html: Optional[str],
) -> bool:
    """Forward the inbound email to Dannion's personal inbox."""
    try:
        if DANIELAYO_EMAIL.lower() in LOCAL_ADDRESSES:
            logger.warning(
                f"Refusing to forward to {DANIELAYO_EMAIL}: this domain "
                "receives for that address, so the forward would loop back in."
            )
            return False
        forward_subject = f"[Dannion] {subject}"
        forward_html = f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Forwarded Email</title></head>
<body style="font-family: -apple-system, sans-serif; padding: 20px;">
    <p><strong>From:</strong> {from_name or ""} &lt;{from_email}&gt;</p>
    <p><strong>Subject:</strong> {subject}</p>
    <hr>
    {body_html or "<pre>" + (body_text or "").replace("<", "&lt;").replace(">", "&gt;") + "</pre>"}
</body>
</html>
"""
        result = await send_email(
            to=DANIELAYO_EMAIL,
            subject=forward_subject,
            html=forward_html,
            text=body_text,
        )
        if result.success:
            logger.info(f"Forwarded inbound email to Dannion: {DANIELAYO_EMAIL}")
            return True
        else:
            logger.error(f"Failed to forward email to Dannion: {result.error}")
            return False
    except Exception as e:
        logger.error(f"Error forwarding to Dannion: {e}")
        return False


async def _store_dmarc_report(
    email_id: str,
    from_email: str,
    subject: str,
    body_text: Optional[str],
    body_html: Optional[str],
) -> bool:
    """Store DMARC aggregate report (don't create a ticket)."""
    try:
        processed = ProcessedWebhook(
            webhook_id=email_id,
            provider="resend",
            event_type="email.received",
            response_sent=False,
            extra_data={
                "from": from_email,
                "subject": subject,
                "destination": "dmarc_report",
                "body_preview": (body_text or "")[:500],
            },
        )
        session.add(processed)
        await session.commit()
        logger.info(f"Stored DMARC report: {email_id}")
        return True
    except Exception as e:
        logger.error(f"Error storing DMARC report: {e}")
        return False

router = APIRouter(prefix="/api/v1/inbound", tags=["inbound"])

# Admin email to forward incoming messages to
SUPPORT_EMAIL = "support@styxproxy.com"
ADMIN_EMAIL = "admin@styxproxy.com"
DANIELAYO_EMAIL = "danielayo@styxproxy.com"
DMARC_EMAIL = "dmarc@styxproxy.com"

# Addresses this domain RECEIVES for. Forwarding to any of them comes straight
# back into this webhook, so a forward whose destination is in this set is a
# loop hop, not a delivery.
LOCAL_ADDRESSES = {SUPPORT_EMAIL, ADMIN_EMAIL, DANIELAYO_EMAIL, DMARC_EMAIL}
FORWARD_PREFIXES = ("[Support]", "[Dannion]")


def _is_loop_message(from_email: str, subject: str, to_addresses: list[str]) -> bool:
    """True when this message was produced by our own forwarding rules.

    admin@ and danielayo@ are on this domain, which Resend also receives for.
    Forwarding an inbound message back to the address that triggered the
    forward makes two rules feed each other:

        admin@ -> "[Support] x" to admin@ -> "[Support] [Support] x" to admin@ ...

    Each hop appends another prefix, so a forward prefix already present in the
    subject, or a sender that is one of our own addresses, is proof this is a
    loop hop rather than a customer message. A real run produced ~76 webhook
    deliveries in 20 seconds and 25+ looping messages.
    """
    subj = (subject or "").strip()
    # strip reply/forward prefixes so "Re: [Support] x" is still caught
    while True:
        low = subj.lower()
        for pre in ("re:", "fwd:", "fw:"):
            if low.startswith(pre):
                subj = subj[len(pre):].strip()
                break
        else:
            break
    if subj.startswith(FORWARD_PREFIXES):
        return True
    if (from_email or "").strip().lower() in LOCAL_ADDRESSES:
        return True
    return False

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


async def _fetch_email_body(email_id: str) -> tuple[Optional[str], Optional[str]]:
    """
    Fetch the email body from the Resend Receiving API.

    Resend's email.received webhook carries metadata only — no body.
    The body must be fetched from GET /emails/receiving/{email_id}.

    Returns (text, html) or (None, None) if the fetch fails.
    """
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=15.0)) as client:
            response = await client.get(
                f"https://api.resend.com/emails/receiving/{email_id}",
                headers={
                    "Authorization": f"Bearer {settings.resend_api_key}",
                    "Content-Type": "application/json",
                },
            )
            if response.status_code == 403:
                logger.warning(
                    f"Receiving API returned 403 for {email_id} — "
                    "key is send-scoped, cannot fetch body"
                )
                return None, None
            if response.status_code >= 400:
                logger.warning(
                    f"Receiving API error for {email_id}: "
                    f"{response.status_code} {response.text[:200]}"
                )
                return None, None
            data = response.json()
            text = data.get("text")
            html = data.get("html")
            if not text and not html:
                logger.warning(f"Receiving API returned empty body for {email_id}")
            return text, html
    except Exception as e:
        logger.warning(f"Failed to fetch email body for {email_id}: {e}")
        return None, None


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
    stmt = select(SupportThread).where(SupportThread.resend_last_message_id == in_reply_to)
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
        stmt = select(SupportThread).where(SupportThread.resend_last_message_id == ref_id.strip("<>"))
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
    """Create a new support thread. The initial message is added by the caller."""
    thread = SupportThread(
        customer_email=from_email,
        customer_name=from_name,
        subject=subject,
        status="open",
    )
    session.add(thread)
    await session.flush()  # Get the ID

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
        # Refuse a destination we also receive for — the forward would re-enter
        # this webhook and feed the loop.
        if ADMIN_EMAIL.lower() in LOCAL_ADDRESSES:
            logger.warning(
                f"Refusing to forward to {ADMIN_EMAIL}: this domain receives "
                "for that address, so the forward would loop back in."
            )
            return False
        # Build a simple forward email
        forward_subject = f"[Support] {subject}"

        # Simple HTML wrapper for forwarded email
        forward_html = f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Forwarded Email</title></head>
<body style="font-family: -apple-system, sans-serif; padding: 20px;">
    <p><strong>From:</strong> {from_name or ""} &lt;{from_email}&gt;</p>
    <p><strong>Subject:</strong> {subject}</p>
    <hr>
    {body_html or "<pre>" + (body_text or "").replace("<", "&lt;").replace(">", "&gt;") + "</pre>"}
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
    # ── Svix signature verification ──────────────────────────────────────
    # Read the raw body for signature verification (FastAPI already parsed it
    # into `payload`, but we need the raw bytes for HMAC)
    body = await request.body()
    if not _verify_svix_signature(request, body):
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing webhook signature",
        )

    # Route bounce / complaint events before they hit the threading logic
    if payload.type == "email.bounced":
        await _handle_bounce(session, payload.data)
        return {"status": "ok", "action": "bounce_recorded"}

    if payload.type == "email.complained":
        await _handle_complaint(session, payload.data)
        return {"status": "ok", "action": "complaint_recorded"}

    # Handle unsubscribe events (user clicked unsubscribe in their email client)
    if payload.type == "email.unsubscribed":
        await _handle_resend_unsubscribe(session, payload.data)
        return {"status": "ok", "action": "unsubscribe_recorded"}

    if payload.type != "email.received":
        logger.warning(f"Ignoring event type: {payload.type}")
        return {"status": "ignored", "reason": f"unhandled: {payload.type}"}

    data = payload.data

    email_id    = data.get("email_id", "")
    from_header = data.get("from", "")
    subject     = data.get("subject", "(No Subject)")
    in_reply_to = data.get("in_reply_to")
    references  = data.get("references")
    text        = data.get("text")
    html        = data.get("html")
    to_addresses = data.get("to", [])

    # Resend's email.received webhook carries metadata only — no body.
    # If both text and html are missing, fetch from the Receiving API.
    if not text and not html and email_id:
        logger.info(f"Webhook payload has no body, fetching from Receiving API: {email_id}")
        text, html = await _fetch_email_body(email_id)
    from_email, from_name = _extract_email_from_header(from_header)

    # ── Loop guard ───────────────────────────────────────────────────────
    # Must run before any branch that forwards: the forward destination is one
    # of our own addresses, so an unguarded forward returns to this handler.
    if _is_loop_message(from_email, subject, to_addresses):
        logger.warning(
            "Loop guard: dropping self-forwarded message "
            f"(from={from_email}, to={to_addresses}, subject={subject[:60]!r})"
        )
        return {"status": "ignored", "reason": "loop_detected"}

    # ── Recipient check ──────────────────────────────────────────────────
    # Route based on recipient address:
    # - support@ → ticket system (SupportThread → /admin/support)
    # - admin@ → errors/management (forward to admin)
    # - danielayo@ → Dannion's personal inbox
    # - dmarc@ → DMARC aggregate reports (store, don't create ticket)
    # - anything else → ignore (don't create ticket)
    
    if SUPPORT_EMAIL in to_addresses:
        pass  # Continue to ticket creation below
    elif ADMIN_EMAIL in to_addresses:
        logger.info(f"Routing admin email to errors/management: {email_id}")
        forwarded = await _forward_to_admin(
            from_email=from_email,
            from_name=from_name,
            subject=subject,
            body_text=text,
            body_html=html,
        )
        return {
            "status": "routed" if forwarded else "not_forwarded",
            "destination": "admin",
            "forwarded": forwarded,
        }
    elif DANIELAYO_EMAIL in to_addresses:
        logger.info(f"Routing danielayo email to Dannion: {email_id}")
        forwarded = await _forward_to_dannion(
            from_email=from_email,
            from_name=from_name,
            subject=subject,
            body_text=text,
            body_html=html,
        )
        return {
            "status": "routed" if forwarded else "not_forwarded",
            "destination": "danielayo",
            "forwarded": forwarded,
        }
    elif DMARC_EMAIL in to_addresses:
        logger.info(f"Storing DMARC report: {email_id}")
        await _store_dmarc_report(
            email_id=email_id,
            from_email=from_email,
            subject=subject,
            body_text=text,
            body_html=html,
        )
        return {"status": "stored", "destination": "dmarc"}
    else:
        logger.info(
            f"Ignoring email to unknown address: {to_addresses} "
            f"(email_id={email_id})"
        )
        return {"status": "ignored", "reason": "unknown_address"}


    # ── Rate limit ──────────────────────────────────────────────────────────
    allowed, remaining = await _check_rate_limit(from_email)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="Too many emails from this sender. Try again later.",
            headers={"Retry-After": "3600"},
        )

    # ── Idempotency ───────────────────────────────────────────────────────
    existing = await session.execute(
        select(ProcessedWebhook).where(ProcessedWebhook.webhook_id == email_id)
    )
    if existing.scalar_one_or_none():
        logger.info(f"Email already processed: {email_id}")
        return {"status": "already_processed", "email_id": email_id}

    # ── Spam ──────────────────────────────────────────────────────────────
    # Don't silently drop — a legitimate customer from a .ru/.cn/etc address
    # must not be invisible. Create the thread but flag it as spam-suspected.
    spam_suspected = _is_spam_sender(from_email)
    if spam_suspected:
        logger.warning(f"Spam-suspected email from: {from_email} — creating thread with flag")

    # ── Auto-close stale threads ───────────────────────────────────────────
    await _auto_close_stale_threads(session)

    # Find or create thread
    thread = None
    if in_reply_to:
        thread = await _find_thread_by_in_reply_to(session, in_reply_to)

    if not thread and references:
        thread = await _find_thread_by_references(session, references)

    # Sanitize HTML to prevent stored XSS — anyone emailing support with an
    # <img onerror> payload can otherwise run script in an admin's browser.
    safe_html = sanitize_html(html) if html else None

    if thread:
        # Add to existing thread
        await _add_message_to_thread(
            session=session,
            thread=thread,
            from_email=from_email,
            to_email=SUPPORT_EMAIL,
            subject=subject,
            body_text=text,
            body_html=safe_html,
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
        await _add_message_to_thread(
            session=session,
            thread=thread,
            from_email=from_email,
            to_email=SUPPORT_EMAIL,
            subject=subject,
            body_text=text,
            body_html=safe_html,
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

    # Forward to admin in background (don't block the webhook response)
    task = asyncio.create_task(
        _forward_to_admin(
            from_email=from_email,
            from_name=from_name,
            subject=subject,
            body_text=text,
            body_html=safe_html,
        )
    )
    _inflight_tasks.add(task)
    task.add_done_callback(_inflight_tasks.discard)
    task.add_done_callback(
        lambda t: logger.error(f"Forward task failed: {t.exception()}")
        if t.exception() else None
    )

    await session.commit()

    return {
        "status": "received",
        "email_id": email_id,
        "thread_id": str(thread.id),
        "rate_limit_remaining": remaining,
    }

# ── Bounce / Complaint handlers ─────────────────────────────────────────────────

async def _handle_resend_unsubscribe(session, data: dict):
    """Record unsubscribe from Resend native list-unsubscribe click."""
    import time as _time
    emails = data.get("emails", [])
    logger.warning(f"email_unsubscribed_via_resend: {emails}")

    for email in emails:
        try:
            from sqlalchemy import select

            from app.models import PlatformAccount, ProcessedWebhook
            stmt = select(PlatformAccount).where(PlatformAccount.email == email.lower())
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()
            if user:
                user.unsubscribed = True
                user.unsubscribed_at = _time.time()
            # Record in ProcessedWebhook for idempotency
            wh_id = f"unsubscribe_{email}_{int(_time.time())}"
            stmt2 = select(ProcessedWebhook).where(ProcessedWebhook.webhook_id == wh_id)
            existing = (await session.execute(stmt2)).scalar_one_or_none()
            if not existing:
                wh = ProcessedWebhook(
                    webhook_id=wh_id,
                    provider="resend",
                    event_type="email.unsubscribed",
                    response_sent=False,
                    extra_data={"email": email, "source": "resend_list_unsubscribe"},
                )
                session.add(wh)
            await session.commit()
        except Exception as e:
            logger.error(f"unsubscribe_handler_error: email={email} error={e}")


async def _handle_bounce(session, data: dict):
    """Record hard bounce → mark user as unsubscribed."""
    import time as _time
    bounced_emails = data.get("emails", [])
    reason = data.get("reason", {}).get("bounce_classification", "unknown")
    logger.warning(f"email_bounced: emails={bounced_emails} reason={reason}")

    for email in bounced_emails:
        try:
            from sqlalchemy import select

            from app.models import PlatformAccount, ProcessedWebhook
            stmt = select(PlatformAccount).where(PlatformAccount.email == email.lower())
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()
            if user:
                user.unsubscribed = True
                user.unsubscribed_at = _time.time()
            wh = ProcessedWebhook(
                webhook_id=f"bounce_{email}_{int(_time.time())}",
                provider="resend",
                event_type="email.bounced",
                response_sent=False,
                extra_data={"email": email, "reason": reason},
            )
            session.add(wh)
            await session.commit()
        except Exception as e:
            logger.error(f"bounce_handler_error: email={email} error={str(e)}")


async def _handle_complaint(session, data: dict):
    """Record spam complaint → mark user as unsubscribed."""
    import time as _time
    complained_emails = data.get("emails", [])
    logger.warning(f"email_complained: emails={complained_emails}")

    for email in complained_emails:
        try:
            from sqlalchemy import select

            from app.models import PlatformAccount, ProcessedWebhook
            stmt = select(PlatformAccount).where(PlatformAccount.email == email.lower())
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()
            if user:
                user.unsubscribed = True
                user.unsubscribed_at = _time.time()
            wh = ProcessedWebhook(
                webhook_id=f"complaint_{email}_{int(_time.time())}",
                provider="resend",
                event_type="email.complained",
                response_sent=False,
                extra_data={"email": email},
            )
            session.add(wh)
            await session.commit()
        except Exception as e:
            logger.error(f"complaint_handler_error: email={email} error={str(e)}")


# ── Unsubscribe endpoint ────────────────────────────────────────────────────────

@router.get("/api/v1/unsubscribe")
async def unsubscribe(
    email: str,
    token: str,
    session: AsyncSession = Depends(get_session),
):
    """
    One-click unsubscribe. Token validates the request (HMAC of email + secret).
    Adds the email to the unsubscribe list so we never email them again.
    """
    import hashlib

    expected = hashlib.sha256(
        f"{email}:styxproxy_unsubscribe_secret_v1".encode()
    ).hexdigest()[:16]
    if token != expected:
        return {"ok": False, "message": "Invalid unsubscribe link."}

    from sqlalchemy import select

    from app.models import PlatformAccount
    stmt = select(PlatformAccount).where(PlatformAccount.email == email.lower())
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    if user:
        user.unsubscribed = True
        import time as _time
        user.unsubscribed_at = _time.time()
        await session.commit()

    return {
        "ok": True,
        "message": "You've been unsubscribed from Styxproxy emails.",
    }


@router.get("/api/v1/unsubscribe/preview")
async def unsubscribe_preview(email: str):
    """Preview page for unsubscribe shown before one-click confirm."""
    import hashlib
    token = hashlib.sha256(
        f"{email}:styxproxy_unsubscribe_secret_v1".encode()
    ).hexdigest()[:16]
    confirm_url = f"https://styxproxy.com/api/v1/unsubscribe?email={email}&token={token}"
    return {
        "email": email,
        "confirm_url": confirm_url,
        "message": "Click confirm_url to unsubscribe.",
    }