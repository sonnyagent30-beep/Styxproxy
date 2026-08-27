"""HTTP endpoint for Charon.

Routes:
  POST /api/v1/charon/reply          — main agent call
  POST /api/v1/charon/reply/stream   — SSE streaming variant
  GET  /api/v1/charon/health         — shallow liveness check
  GET  /api/v1/charon/conversations  — list all conversations
  GET  /api/v1/charon/logs           — filterable logs
  GET  /api/v1/charon/stream         — SSE live event stream

The endpoint is intentionally unauthenticated for the prototype —
Charon is designed to be a public support surface. When it goes
to production we'll layer an internal-token gateway in front, but
that's separate from agent auth (which the agent's tools enforce
themselves).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import text

from app.auth import decode_access_token, verify_admin_token
from app.database import async_session
from app.limiter import limiter
from app.services.charon import agent
from app.services.charon.agent import Message
from app.services.charon.knowledge import invalidate_cache
from app.services.charon.stats import CharonMetrics
from app.services.email import send_charon_escalation_email

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/charon", tags=["charon"])


async def public_only(request: Request) -> None:
    """Reject any request that carries a valid admin Bearer token.

    Charon is a public customer-support surface. Admin sessions must NOT
    trigger the chat agent — they have their own dashboard endpoints at
    /api/admin/charon/stats. If we let admin tokens through, every
    admin browser navigation would consume LLM tokens and pollute the
    anonymous metrics with non-customer traffic.

    Styxproxy has TWO auth systems for staff:
      1. JWT access tokens (issued by /api/auth/login) — what the React
         dashboard uses; validated via decode_access_token().
      2. ADMIN_TOKEN static secret (settings.admin_token) — for
         health-checks, scripts, and a few legacy callers; validated
         via verify_admin_token().

    Both count as "admin traffic" for the purposes of this gate.

    Behavior:
      - No Authorization header                 → pass through
      - Malformed Bearer (no token after "Bearer") → pass through
      - Any unknown or expired token            → pass through
      - Valid JWT (admin or superadmin role)    → 404
      - Valid static ADMIN_TOKEN                → 404
    """
    auth_header = request.headers.get("Authorization") or request.headers.get("authorization")
    if not auth_header:
        return

    parts = auth_header.split()
    if len(parts) < 2:
        return
    if parts[0].lower() != "bearer":
        return
    token = parts[1]
    if not token:
        return

    is_admin = False
    # Path 1: JWT (dashboard auth).
    try:
        payload = decode_access_token(token)
        # JWTs issued by /api/auth/login have "email" + "platform" set.
        # Anything decodeable is considered an admin token here.
        if payload.get("email") or payload.get("sub"):
            is_admin = True
    except HTTPException:
        pass

    # Path 2: static ADMIN_TOKEN (legacy / scripts).
    if not is_admin:
        try:
            if verify_admin_token(auth_header):
                is_admin = True
        except HTTPException:
            pass

    if is_admin:
        # Use 404, not 403, so endpoint existence stays private.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not Found",
        )


# Log file path
CHARON_LOG_DIR = os.getenv("CHARON_LOG_DIR", "/tmp")
CHARON_LOG_PATH = os.path.join(CHARON_LOG_DIR, "charon.log")  # nosec B108


class ChatMessage(BaseModel):
    role: str = Field(..., description="One of 'system' | 'user' | 'assistant'.")
    content: str = Field(..., description="Message body.")


class ChatReplyRequest(BaseModel):
    channel: str = Field(default="web", description="Channel label: web|telegram|whatsapp|internal.")
    conversation_id: Optional[str] = Field(default=None)
    user_message: str = Field(..., min_length=1, max_length=4000)
    history: list[ChatMessage] = Field(default_factory=list)
    customer_email: Optional[str] = Field(default=None, description="Customer email for escalation notifications")
    customer_phone: Optional[str] = Field(default=None, description="Customer phone for escalation notifications")


class ToolCallRecord(BaseModel):
    tool: str
    params: dict
    result: Optional[dict] = None
    error: Optional[str] = None


class ChatReplyResponse(BaseModel):
    text: str
    scenario_id: Optional[str] = None
    escalated: bool = False
    tool_calls: list[ToolCallRecord] = []
    tokens_used: int = 0
    error: Optional[str] = None


class ConversationSummary(BaseModel):
    conversation_id: str
    last_message: str
    last_message_at: str
    message_count: int
    escalated: bool


class CharonLogEntry(BaseModel):
    ts: str
    channel: str
    conversation_id: str
    user_message: str
    response: Optional[str] = None
    scenario_id: Optional[str] = None
    escalated: Optional[bool] = None
    error: Optional[str] = None
    tool_calls: Optional[list[dict]] = None


@router.post("/reply", response_model=ChatReplyResponse)
@limiter.limit("30/minute")
async def post_reply(
    payload: ChatReplyRequest,
    request: Request,
    _public: None = Depends(public_only),
):
    """Synchronous chat reply.

    For the bulk of customer support questions this is the right
    entrypoint — one request, one response, simple to instrument.
    Streaming is available below for low-latency interactive use.
    """
    import time

    if not payload.user_message.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="user_message cannot be empty",
        )

    from app.services.charon.stats import CharonMetrics

    # Check daily cost budget before spending any tokens
    allowed, spend, budget = CharonMetrics.check_budget()
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Charon daily budget exhausted ({spend:.4f}/{budget:.4f} USD). Resets at midnight.",
        )

    CharonMetrics.mark_request(payload.channel)

    history = [
        Message(role=m.role, content=m.content) for m in payload.history if m.role in ("system", "user", "assistant")
    ]

    started = time.perf_counter()
    result = await agent.reply(
        channel=payload.channel,
        conversation_id=payload.conversation_id or "",
        user_message=payload.user_message,
        history=history,
    )
    elapsed_ms = (time.perf_counter() - started) * 1000.0

    # Observability
    CharonMetrics.record_latency(elapsed_ms)
    if result.escalated:
        CharonMetrics.mark_escalated(reason=result.error or "scenario_escalate")
    if result.error:
        CharonMetrics.mark_llm_error(result.error)
    elif result.tokens_used:
        CharonMetrics.mark_success(result.tokens_used, elapsed_ms)
        CharonMetrics.record_spend(result.tokens_used)
    if result.scenario_id and not result.error:
        CharonMetrics.mark_scenario_hit(result.scenario_id)

    # Send escalation email if the conversation was escalated
    if result.escalated and (payload.customer_email or payload.customer_phone):
        # Build history summary for the email
        history_summary = "\n".join(f"{m.role}: {m.content[:200]}" for m in history[-5:])
        await send_charon_escalation_email(
            conversation_id=payload.conversation_id or "unknown",
            customer_email=payload.customer_email,
            customer_phone=payload.customer_phone,
            message=payload.user_message,
            history_summary=history_summary,
        )
    
    # Persist assistant message
    from app.services.charon.agent import _persist_message
    await _persist_message(
        payload.conversation_id or "unknown",
        payload.channel,
        "assistant",
        result.text,
        tool_calls=result.tool_calls,
        tokens_used=result.tokens_used,
    )

    return ChatReplyResponse(
        text=result.text,
        scenario_id=result.scenario_id,
        escalated=result.escalated,
        tool_calls=[
            ToolCallRecord(
                tool=c.get("tool", ""),
                params=c.get("params", {}),
                result=c.get("result"),
                error=c.get("error"),
            )
            for c in result.tool_calls
        ],
        tokens_used=result.tokens_used,
        error=result.error,
    )


@router.get("/health")
async def health():
    """Liveness check. Always returns ok unless the route is fully down.

    Distinguishes:
      - configured: whether the LLM API key is set
      - last_success: when the LLM last replied with content
      - last_error: when an LLM error was last seen
      - llm_status: "up" / "degraded" / "down"
    """
    import os

    from app.services.charon import scenarios

    # P0-5 (Jul 22 2026): Provider priority is M2 cloud primary,
    # MiniCPM5 local fallback. Probe BOTH and report each so the
    # admin dashboard can see whether the fallback path is also up.
    cloud_key_set = bool(os.getenv("MINIMAX_API_KEY"))

    # Probe LiteLLM (local fallback reachability).
    local_reachable = False
    try:
        base = os.getenv("LITELLM_BASE_URL", "http://127.0.0.1:4000").rstrip("/")
        probe = httpx.get(f"{base}/health/liveliness", timeout=2.0)
        local_reachable = probe.status_code == 200
    except Exception:
        local_reachable = False

    # Configuration gate: primary is M2 cloud, so this is what the
    # primary path needs. Local is bonus.
    api_key_set = cloud_key_set
    CharonMetrics.llm_configured(api_key_set)

    s = CharonMetrics.get()
    error_age = time.time() - s.llm_last_error_at if s.llm_last_error_at else None
    success_age = time.time() - s.llm_last_success_at if s.llm_last_success_at else None

    if not api_key_set:
        llm_status = "down"
    elif s.llm_errors > 0 and (error_age is not None and (success_age is None or error_age < success_age)):
        llm_status = "degraded"
    elif s.llm_last_success_at is None and s.total_requests > 0:
        llm_status = "degraded"
    else:
        llm_status = "up"

    return {
        "ok": True,
        "module": "charon",
        "llm_configured": api_key_set,
        "llm_status": llm_status,
        "total_requests": s.total_requests,
        "escalated_replies": s.escalated_replies,
    }


@router.get("/_internal/stats")
async def _internal_stats():
    """Detailed Charon stats. Unauthenticated but obscure URL.

    The superadmin dashboard reads this via a wrapper at
    /api/admin/charon/stats which enforces JWT auth.
    """
    return CharonMetrics.get().to_dict()


def _read_logs(limit: int = 1000) -> list[dict]:
    """Read logs from the JSONL file."""
    logs = []
    if not os.path.exists(CHARON_LOG_PATH):
        return logs
    try:
        with open(CHARON_LOG_PATH, "r") as f:
            lines = f.readlines()
        for line in lines[-limit:]:
            try:
                logs.append(json.loads(line.strip()))
            except json.JSONDecodeError:
                continue
    except OSError:
        pass
    return logs


def _get_conversations() -> list[ConversationSummary]:
    """Extract unique conversations from logs."""
    conversations: dict[str, dict] = {}
    logs = _read_logs(limit=5000)

    for log in logs:
        conv_id = log.get("conversation_id")
        if not conv_id:
            continue
        if conv_id not in conversations:
            conversations[conv_id] = {
                "conversation_id": conv_id,
                "last_message": log.get("user_message", "")[:100],
                "last_message_at": log.get("ts", ""),
                "message_count": 0,
                "escalated": log.get("escalated", False),
            }
        conversations[conv_id]["message_count"] += 1
        # Update with latest
        conversations[conv_id]["last_message"] = log.get("user_message", "")[:100]
        conversations[conv_id]["last_message_at"] = log.get("ts", "")
        if log.get("escalated"):
            conversations[conv_id]["escalated"] = True

    return [ConversationSummary(**conv) for conv in conversations.values()]


@router.get("/conversations")
async def list_conversations(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    _public: None = Depends(public_only),
):
    """List all Charon conversations with summary info."""
    all_conversations = _get_conversations()
    total = len(all_conversations)
    # Sort by last_message_at descending
    all_conversations.sort(key=lambda x: x.last_message_at, reverse=True)
    return {
        "conversations": all_conversations[offset : offset + limit],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/logs")
async def list_logs(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    conversation_id: Optional[str] = Query(None),
    channel: Optional[str] = Query(None),
    _public: None = Depends(public_only),
    escalated: Optional[bool] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
):
    """Filterable logs for Charon conversations."""
    logs = _read_logs(limit=5000)

    # Apply filters
    filtered = []
    for log in logs:
        if conversation_id and log.get("conversation_id") != conversation_id:
            continue
        if channel and log.get("channel") != channel:
            continue
        if escalated is not None and log.get("escalated") != escalated:
            continue
        if date_from:
            log_ts = log.get("ts", "")
            if log_ts and log_ts < date_from:
                continue
        if date_to:
            log_ts = log.get("ts", "")
            if log_ts and log_ts > date_to:
                continue
        filtered.append(log)

    # Sort by ts descending
    filtered.sort(key=lambda x: x.get("ts", ""), reverse=True)

    total = len(filtered)
    return {
        "logs": filtered[offset : offset + limit],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


# SSE event subscribers
_sse_subscribers: set[asyncio.Queue] = set()


async def _broadcast_event(event_type: str, data: dict):
    """Broadcast an event to all SSE subscribers."""
    event = f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
    for queue in _sse_subscribers:
        try:
            await queue.put(event)
        except Exception:
            pass


@router.get("/stream")
@limiter.limit("10/minute")
async def stream_events(request: Request):
    """SSE stream for real-time Charon events."""
    queue: asyncio.Queue = asyncio.Queue()
    _sse_subscribers.add(queue)

    async def event_generator():
        try:
            # Send initial connection event
            yield 'event: connected\ndata: {"status": "connected"}\n\n'

            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30)
                    yield event
                except asyncio.TimeoutError:
                    # Send keepalive
                    yield ": keepalive\n\n"
        except GeneratorExit:
            pass
        finally:
            _sse_subscribers.discard(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# Hook into agent to broadcast events
def _install_event_hook():
    """Install the event broadcast hook into the agent module."""
    import app.services.charon.agent as agent_module

    original_persist = agent_module._persist_log

    def hooked_persist(ctx: dict):
        original_persist(ctx)
        # Broadcast to SSE subscribers
        asyncio.create_task(_broadcast_event("charon.log", ctx))

    agent_module._persist_log = hooked_persist


# Install the hook on module load
try:
    _install_event_hook()
except Exception:
    pass  # Best-effort


# =============================================================================
# LEARN ENDPOINT - Write learned content to RAG knowledge base
# =============================================================================


class LearnRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200, description="Title/heading for the learned content")
    content: str = Field(..., min_length=1, max_length=50000, description="Markdown content to learn")
    filename: Optional[str] = Field(default=None, description="Optional custom filename (without .md)")


class LearnResponse(BaseModel):
    ok: bool
    filepath: str
    message: str


# Directory for learned content
LEARNED_DIR = Path(__file__).parents[3] / "data" / "charon" / "learned"


def _sanitize_filename(name: str) -> str:
    """Convert a string into a safe filename."""
    # Replace spaces with hyphens, lowercase
    sanitized = name.lower().strip()
    # Remove anything that's not alphanumeric, hyphen, or underscore
    sanitized = re.sub(r"[^a-z0-9\-_]", "-", sanitized)
    # Collapse multiple hyphens into one
    sanitized = re.sub(r"-+", "-", sanitized)
    # Strip leading/trailing hyphens
    sanitized = sanitized.strip("-")
    # Limit length
    return sanitized[:100] or "untitled"


@router.post("/learn", response_model=LearnResponse)
async def post_learn(
    payload: LearnRequest,
    _public: None = Depends(public_only),
):
    """Write learned content to the RAG knowledge base.

    Content is saved as a markdown file in data/charon/learned/ and
    becomes available to Charon's RAG search on next query.
    """
    # Ensure learned directory exists
    LEARNED_DIR.mkdir(parents=True, exist_ok=True)

    # Generate filename
    if payload.filename:
        base_name = _sanitize_filename(payload.filename)
    else:
        # Use title to generate filename with timestamp
        timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        base_name = f"{_sanitize_filename(payload.title[:50])}-{timestamp}"

    # Ensure .md extension
    if not base_name.endswith(".md"):
        base_name += ".md"

    filepath = LEARNED_DIR / base_name

    # Handle duplicate filenames
    counter = 1
    while filepath.exists():
        base, ext = base_name.rsplit(".md", 1)
        filepath = LEARNED_DIR / f"{base}-{counter}.md"
        counter += 1

    # Write the content with a header
    content = f"# {payload.title}\n\n{payload.content}"
    filepath.write_text(content, encoding="utf-8")

    # Invalidate the RAG cache so new content is picked up
    invalidate_cache()

    return LearnResponse(
        ok=True,
        filepath=str(filepath.relative_to(LEARNED_DIR.parent.parent)),
        message=f"Successfully saved to {filepath.name}",
    )


# =============================================================================
# TRIGGER ENDPOINTS - Record and query trigger event weights
# =============================================================================


class TriggerEventRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=64)
    trigger_id: str = Field(..., min_length=1, max_length=50)
    outcome: str = Field(..., description="One of: opened_chat, dismissed, ignored, converted")
    charon_msg: Optional[str] = Field(default=None, description="Optional Charon message that was shown")


VALID_OUTCOMES = {"opened_chat", "dismissed", "ignored", "converted"}


@router.post("/trigger-event")
async def post_trigger_event(payload: TriggerEventRequest):
    """Record a trigger outcome and update aggregate weights.

    This endpoint records how users responded to behavioral triggers
    (e.g., repeat_pricing, cart_abandon). The outcome updates:
    - total_fires (always +1)
    - total_opens (if opened_chat or converted)
    - total_dismissed (if dismissed)
    - total_converted (if converted)
    - positive_rate = (opens + converted * 1.5) / total_fires
    """
    # Validate outcome
    if payload.outcome not in VALID_OUTCOMES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid outcome. Must be one of: {', '.join(VALID_OUTCOMES)}",
        )

    async with async_session() as session:
        # Insert trigger event
        await session.execute(
            text("""
                INSERT INTO trigger_events (session_id, trigger_id, outcome, charon_msg)
                VALUES (:session_id, :trigger_id, :outcome, :charon_msg)
            """),
            {
                "session_id": payload.session_id,
                "trigger_id": payload.trigger_id,
                "outcome": payload.outcome,
                "charon_msg": payload.charon_msg,
            },
        )

        # Determine counter updates based on outcome
        if payload.outcome == "opened_chat":
            update_sql = """
                UPDATE trigger_weights
                SET total_fires = total_fires + 1,
                    total_opens = total_opens + 1,
                    positive_rate = (total_opens + 1 + total_converted * 1.5) / (total_fires + 1),
                    updated_at = NOW()
                WHERE trigger_id = :trigger_id
            """
        elif payload.outcome == "dismissed":
            update_sql = """
                UPDATE trigger_weights
                SET total_fires = total_fires + 1,
                    total_dismissed = total_dismissed + 1,
                    positive_rate = (total_opens + total_converted * 1.5) / (total_fires + 1),
                    updated_at = NOW()
                WHERE trigger_id = :trigger_id
            """
        elif payload.outcome == "converted":
            update_sql = """
                UPDATE trigger_weights
                SET total_fires = total_fires + 1,
                    total_opens = total_opens + 1,
                    total_converted = total_converted + 1,
                    positive_rate = (total_opens + 1 + (total_converted + 1) * 1.5) / (total_fires + 1),
                    updated_at = NOW()
                WHERE trigger_id = :trigger_id
            """
        else:  # ignored
            update_sql = """
                UPDATE trigger_weights
                SET total_fires = total_fires + 1,
                    positive_rate = (total_opens + total_converted * 1.5) / (total_fires + 1),
                    updated_at = NOW()
                WHERE trigger_id = :trigger_id
            """

        await session.execute(text(update_sql), {"trigger_id": payload.trigger_id})
        await session.commit()

    return {"ok": True}


@router.get("/weights")
async def get_weights():
    """Get all trigger weights.

    Returns a dict mapping trigger_id to {weight, total_fires}.
    """
    async with async_session() as session:
        result = await session.execute(
            text("""
                SELECT trigger_id, weight, total_fires
                FROM trigger_weights
                ORDER BY trigger_id
            """)
        )
        rows = result.fetchall()

    weights = {row[0]: {"weight": float(row[1]), "total_fires": row[2]} for row in rows}
    return {"weights": weights}


# ─── Conversation Persistence Endpoints ────────────────────────────────────

class ConversationListRequest(BaseModel):
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)
    status: Optional[str] = None
    escalated: Optional[bool] = None


@router.get("/conversations")
async def list_conversations_db(req: ConversationListRequest):
    """List conversations from database (persistent storage)."""
    from app.models import CharonConversation, CharonMessage
    from sqlalchemy import select
    
    async with async_session() as session:
        stmt = select(CharonConversation).order_by(CharonConversation.last_activity_at.desc())
        
        if req.status:
            stmt = stmt.where(CharonConversation.status == req.status)
        if req.escalated is not None:
            stmt = stmt.where(CharonConversation.escalated == req.escalated)
        
        stmt = stmt.offset(req.offset).limit(req.limit)
        result = await session.execute(stmt)
        conversations = result.scalars().all()
        
        return {
            "conversations": [
                {
                    "id": str(c.id),
                    "session_id": c.session_id,
                    "channel": c.channel,
                    "status": c.status,
                    "escalated": c.escalated,
                    "message_count": c.message_count,
                    "tokens_used": c.tokens_used,
                    "rating": c.rating,
                    "started_at": c.started_at.isoformat() if c.started_at else None,
                    "last_activity_at": c.last_activity_at.isoformat() if c.last_activity_at else None,
                }
                for c in conversations
            ],
            "limit": req.limit,
            "offset": req.offset,
        }


@router.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    """Get a single conversation with all messages."""
    from app.models import CharonConversation, CharonMessage
    from sqlalchemy import select
    
    async with async_session() as session:
        # Get conversation
        conv_stmt = select(CharonConversation).where(CharonConversation.id == conversation_id)
        conv_result = await session.execute(conv_stmt)
        conv = conv_result.scalar_one_or_none()
        
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Get messages
        msg_stmt = select(CharonMessage).where(CharonMessage.conversation_id == conversation_id).order_by(CharonMessage.ts)
        msg_result = await session.execute(msg_stmt)
        messages = msg_result.scalars().all()
        
        return {
            "conversation": {
                "id": str(conv.id),
                "session_id": conv.session_id,
                "channel": conv.channel,
                "status": conv.status,
                "escalated": conv.escalated,
                "escalation_reason": conv.escalation_reason,
                "rating": conv.rating,
                "rating_comment": conv.rating_comment,
                "message_count": conv.message_count,
                "tokens_used": conv.tokens_used,
                "page_context": conv.page_context,
                "experiment_variant": conv.experiment_variant,
                "started_at": conv.started_at.isoformat() if conv.started_at else None,
                "last_activity_at": conv.last_activity_at.isoformat() if conv.last_activity_at else None,
            },
            "messages": [
                {
                    "id": str(m.id),
                    "role": m.role,
                    "content": m.content,
                    "tool_calls": m.tool_calls,
                    "tokens_used": m.tokens_used,
                    "ts": m.ts.isoformat() if m.ts else None,
                }
                for m in messages
            ],
        }


class RatingRequest(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None


@router.post("/conversations/{conversation_id}/rate")
async def rate_conversation(conversation_id: str, req: RatingRequest):
    """Rate a conversation (1-5 stars)."""
    from app.models import CharonConversation
    from sqlalchemy import select
    
    async with async_session() as session:
        stmt = select(CharonConversation).where(CharonConversation.id == conversation_id)
        result = await session.execute(stmt)
        conv = result.scalar_one_or_none()
        
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        conv.rating = req.rating
        conv.rating_comment = req.comment
        await session.commit()
        
        return {"ok": True, "rating": req.rating}


# ─── Context Summary Endpoint ──────────────────────────────────────────────

class ContextRequest(BaseModel):
    messages: list[dict]
    topics: list[str] = []


@router.post("/context")
async def save_context(req: ContextRequest):
    """Generate and save a context summary for the conversation."""
    from app.services.charon.agent import _save_context_summary
    from app.services.charon.llm import call_llm
    
    # Build summary from messages
    history_text = "\n".join(f"{m['role']}: {m['content']}" for m in req.messages)
    topics_str = ", ".join(req.topics) if req.topics else "general"
    
    summary_prompt = f"""Summarize this customer support conversation in 2-3 sentences. Focus on:
1. What the customer needed
2. Whether it was resolved
3. Any follow-up actions needed

Topics: {topics_str}

Conversation:
{history_text}

Summary:"""
    
    try:
        result = call_llm([
            {"role": "system", "content": "You are a conversation summarizer. Be concise and factual."},
            {"role": "user", "content": summary_prompt},
        ], max_tokens=200)
        
        if result.ok:
            summary = result.content
        else:
            summary = f"Customer discussed: {topics_str}"
    except Exception:
        summary = f"Customer discussed: {topics_str}"
    
    # Extract intent from last user message
    last_user_msg = next((m['content'] for m in reversed(req.messages) if m['role'] == 'user'), None)
    intent = last_user_msg[:100] if last_user_msg else None
    
    # Save summary
    await _save_context_summary(
        conversation_id="web-session",
        summary=summary,
        message_count=len(req.messages),
        last_intent=intent,
        last_topics=req.topics,
    )
    
    return {"ok": True, "summary": summary}
