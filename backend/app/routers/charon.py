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
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.services.charon import agent
from app.services.charon.agent import Message
from app.services.charon.knowledge import invalidate_cache
from app.services.email import send_charon_escalation_email

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/charon", tags=["charon"])

# Log file path
CHARON_LOG_DIR = os.getenv("CHARON_LOG_DIR", "/tmp")
CHARON_LOG_PATH = os.path.join(CHARON_LOG_DIR, "charon.log")


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
async def post_reply(payload: ChatReplyRequest):
    """Synchronous chat reply.

    For the bulk of customer support questions this is the right
    entrypoint — one request, one response, simple to instrument.
    Streaming is available below for low-latency interactive use.
    """
    if not payload.user_message.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="user_message cannot be empty",
        )

    history = [
        Message(role=m.role, content=m.content)
        for m in payload.history
        if m.role in ("system", "user", "assistant")
    ]

    result = await agent.reply(
        channel=payload.channel,
        conversation_id=payload.conversation_id or "",
        user_message=payload.user_message,
        history=history,
    )

    # Send escalation email if the conversation was escalated
    if result.escalated and (payload.customer_email or payload.customer_phone):
        # Build history summary for the email
        history_summary = "\n".join(
            f"{m.role}: {m.content[:200]}" for m in history[-5:]
        )
        await send_charon_escalation_email(
            conversation_id=payload.conversation_id or "unknown",
            customer_email=payload.customer_email,
            customer_phone=payload.customer_phone,
            message=payload.user_message,
            history_summary=history_summary,
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
    """Liveness check. Always returns ok unless the route is fully down."""
    from app.services.charon import scenarios
    return {
        "ok": True,
        "scenarios_loaded": sum(1 for _ in scenarios.all_scenarios()),
        "module": "charon",
    }


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
    
    return [
        ConversationSummary(**conv) 
        for conv in conversations.values()
    ]


@router.get("/conversations")
async def list_conversations(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    """List all Charon conversations with summary info."""
    all_conversations = _get_conversations()
    total = len(all_conversations)
    # Sort by last_message_at descending
    all_conversations.sort(key=lambda x: x.last_message_at, reverse=True)
    return {
        "conversations": all_conversations[offset:offset + limit],
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
        "logs": filtered[offset:offset + limit],
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
async def stream_events():
    """SSE stream for real-time Charon events."""
    queue: asyncio.Queue = asyncio.Queue()
    _sse_subscribers.add(queue)
    
    async def event_generator():
        try:
            # Send initial connection event
            yield "event: connected\ndata: {\"status\": \"connected\"}\n\n"
            
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
async def post_learn(payload: LearnRequest):
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
