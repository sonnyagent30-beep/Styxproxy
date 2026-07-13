"""HTTP endpoint for Charon.

Routes:
  POST /api/v1/charon/reply          — main agent call
  POST /api/v1/charon/reply/stream   — SSE streaming variant
  GET  /api/v1/charon/health         — shallow liveness check

The endpoint is intentionally unauthenticated for the prototype —
Charon is designed to be a public support surface. When it goes
to production we'll layer an internal-token gateway in front, but
that's separate from agent auth (which the agent's tools enforce
themselves).
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.services.charon import agent
from app.services.charon.agent import Message

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/charon", tags=["charon"])


class ChatMessage(BaseModel):
    role: str = Field(..., description="One of 'system' | 'user' | 'assistant'.")
    content: str = Field(..., description="Message body.")


class ChatReplyRequest(BaseModel):
    channel: str = Field(default="web", description="Channel label: web|telegram|whatsapp|internal.")
    conversation_id: Optional[str] = Field(default=None)
    user_message: str = Field(..., min_length=1, max_length=4000)
    history: list[ChatMessage] = Field(default_factory=list)


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
