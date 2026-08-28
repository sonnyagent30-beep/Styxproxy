"""Charon agent orchestrator."""
from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
import re
import uuid
from dataclasses import dataclass, field
from typing import Any, Iterable

import sentry_sdk

from app.services.charon.page_templates import get_page_prompt_addition
from app.services.charon.ab_framework import get_variant, get_page_context_variant, record_outcome
from app.services.charon.escalation_persist import persist_escalation_sync
from . import knowledge, scenarios, tools
from .llm import LLMResponse, call_llm

logger = logging.getLogger(__name__)


@dataclass
class Reply:
    text: str
    scenario_id: str | None = None
    tool_calls: list[dict] = field(default_factory=list)
    escalated: bool = False
    error: str | None = None
    tokens_used: int = 0
    raw: dict | None = None
    experiment_variant: str | None = None


@dataclass
class Message:
    role: str
    content: str


_TX_REF_PATTERN = re.compile(
    r"\b(?:STX|TX|TXF|TXF-ORD|ORD)-\d{4,}[A-Z0-9\-]*\b|" r"\b[A-Z0-9]{6,12}-\d{4,}\b",
    re.IGNORECASE,
)

# Thinking-trace guard: strip any internal monologue the model leaks.
_THINK_BLOCKS = [
    re.compile(
        r"<(?:think|thinking|reasoning|scratchpad)>.*?</(?:think|thinking|reasoning|scratchpad)>",
        re.DOTALL | re.IGNORECASE,
    ),
    re.compile(
        r"\[(?:think|thinking|reasoning|scratchpad)\].*?\[/(?:think|thinking|reasoning|scratchpad)\]",
        re.DOTALL | re.IGNORECASE,
    ),
]
# Fenced code blocks the model sometimes emits when it wasn't asked for code.
_FENCED_CODE = re.compile(r"```[a-zA-Z0-9_+\-]*\n.*?\n```", re.DOTALL)
# Markdown table syntax -> flatten into prose so chat surfaces stay readable.
_TABLE_ROW = re.compile(r"^\s*\|.*\|\s*$", re.MULTILINE)
_TABLE_SEPARATOR = re.compile(r"^\s*\|?[\s:\-|]+\|?\s*$", re.MULTILINE)
# Runaway blank lines.
_BLANK_RUN = re.compile(r"\n{3,}")


def _clean_reply(text: str) -> str:
    """Sanitize an LLM reply before sending it to a customer channel.

    Removes leaked thinking traces, raw code fences, and raw markdown table
    pipes; collapses random blank lines. Keeps prose, bullets, and pricing
    numbers tidy. Never raises — returns the original text if cleaning fails.
    """
    if not text:
        return text
    out = text

    # 1. Drop thinking blocks the model accidentally leaked.
    for pat in _THINK_BLOCKS:
        out = pat.sub("", out)

    # 2. Drop fenced code blocks — chat surface doesn't render them.
    out = _FENCED_CODE.sub("", out)

    # 3. Convert pipe-table rows to a single tidy line per row.
    lines = out.splitlines()
    cleaned: list[str] = []
    table_buf: list[str] = []

    def flush_table() -> None:
        if not table_buf:
            return
        # Strip leading/trailing pipes, drop separator row (---:|---|---).
        rows: list[list[str]] = []
        for row in table_buf:
            if _TABLE_SEPARATOR.match(row):
                continue
            cells = [c.strip() for c in row.strip().strip("|").split("|")]
            rows.append(cells)
        if not rows:
            table_buf.clear()
            return
        # Header row -> "Header: a, b, c" then each data row as "• a: b, c".
        if len(rows) >= 2:
            header = " / ".join(rows[0])
            cleaned.append(f"{header}:")
            for r in rows[1:]:
                pairs = [f"{a} {b}".strip() for a, b in zip(rows[0], r) if a and b]
                cleaned.append("  • " + "; ".join(pairs))
        elif len(rows) == 1:
            cleaned.append("  • " + " | ".join(rows[0]))
        table_buf.clear()

    for line in lines:
        if _TABLE_ROW.match(line):
            table_buf.append(line)
        else:
            flush_table()
            cleaned.append(line)
    flush_table()

    out = "\n".join(cleaned)
    # 4. Tidy whitespace.
    out = _BLANK_RUN.sub("\n\n", out).strip()
    return out


def _extract_tx_ref(messages: Iterable[Message]) -> str | None:
    for msg in reversed(list(messages)[-3:]):
        matches = _TX_REF_PATTERN.findall(msg.content or "")
        if matches:
            return matches[0].upper()
    return None


def _serialize_history(history: Iterable[Message]) -> list[dict]:
    out = []
    for msg in history:
        out.append({"role": msg.role, "content": msg.content})
    return out


async def reply(
    channel: str,
    conversation_id: str,
    user_message: str,
    *,
    history: list[Message] | None = None,
    page_context: dict | None = None,
) -> Reply:
    """End-to-end Charon reply.

    Order of operations:
    0. Persist user message to DB
    1. Try scenario matcher — deterministic, free, fast.
    2. Try LLM with knowledge context + tool definitions.
    3. Fall back to "I am having trouble; escalate" if LLM fails.
    """
    conversation_id = conversation_id or str(uuid.uuid4())
    variant = get_variant(conversation_id)
    
    # Persist user message
    await _persist_message(conversation_id, channel, "user", user_message, page_context=page_context)
    
    log_ctx: dict[str, Any] = {
        "channel": channel,
        "conversation_id": conversation_id,
        "user_message": user_message[:500],
        "experiment_variant": variant.value,
    }

    messages = list(history or [])
    messages.append(Message(role="user", content=user_message))

    # ── 0. Conversation timeout ──────────────────────────────────────
    # If conversation has gone on too long, escalate to human
    CONVERSATION_TURN_LIMIT = 10
    user_turns = sum(1 for m in messages if m.role == "user")
    if user_turns > CONVERSATION_TURN_LIMIT:
        return Reply(
            text="This conversation has been going on for a while. Let me connect you with a human who can help better.",
            escalated=True,
            error="conversation_timeout",
        )

    # ── 1. Scenario matcher ──────────────────────────────────────────
    scenario = scenarios.match(user_message)
    if scenario:
        reply_action, escalate = _run_scenario(scenario, messages, conversation_id=conversation_id, customer_email=None, customer_phone=None, customer_message=user_message, history_summary="")
        log_ctx["scenario_id"] = scenario.id
        log_ctx["response"] = reply_action.text
        log_ctx["escalated"] = escalate
        _persist_log(log_ctx)
        return Reply(text=reply_action.text, scenario_id=scenario.id, escalated=escalate, experiment_variant=variant.value)

    # ── 1b. Per-conversation budget cap ─────────────────────────────
    # Prevent runaway conversations from spending too much
    MAX_TOKENS_PER_CONVERSATION = 8000
    history_tokens = sum(len(m.content or "") for m in messages) // 4  # rough estimate
    if history_tokens > MAX_TOKENS_PER_CONVERSATION:
        return Reply(
            text="I've spent a lot of time on this. Let me escalate to the team for better help.",
            escalated=True,
            error="conversation_budget_exhausted",
        )

    # ── 2. LLM with knowledge + tools ──────────────────────────────
    context_chunks = knowledge.search(user_message, top_k=4)
    context_text = knowledge.format_context(context_chunks)
    
    # Load previous context summary if exists
    context_summary = await _load_context_summary(conversation_id)
    if context_summary:
        context_text = f"Previous conversation summary:\n{context_summary}\n\n{context_text}"

    tx_ref = _extract_tx_ref(messages)
    history_dicts = _serialize_history(messages[-8:])  # 8 turns of context is plenty for QA

    # A/B: treatment group gets page context, control gets None
    filtered_context, _ = get_page_context_variant(conversation_id, page_context)
    page_prompt = get_page_prompt_addition(filtered_context)

    system_block = (
        "You may use these tools if relevant. Call them only when useful; "
        "you do not need to call a tool to answer. Tools are read-only — "
        "you cannot mutate orders, payments, or credentials. If the customer "
        "asks for a mutation (refund, replacement, cancellation), you must "
        "decline and offer to escalate. Use suggest_articles or "
        "get_product_catalog before guessing.\n\n"
        f"Available tools:\n{json.dumps(tools.registry.list_specs(), indent=2)}\n\n"
        f"Known transaction reference (if any): {tx_ref or 'none mentioned yet'}\n\n"
        f"Knowledge base context:\n{context_text}\n"
        + (f"\n\n{page_prompt}" if page_prompt else "")
    )

    # ── 2a. Try a tool-calling loop. If the LLM doesn't speak tool
    #       calling format cleanly, we fall through to a plain prompt.
    tool_call_result = await _try_tool_call(
        channel=channel,
        messages=history_dicts,
        extra_system=system_block,
        user_message=user_message,
        tx_ref=tx_ref,
        log_ctx=log_ctx,
    )
    if tool_call_result is not None:
        log_ctx["response"] = tool_call_result.text
        _persist_log(log_ctx)
        # Fire-and-forget: don't block the response on experiment tracking
        asyncio.create_task(record_outcome(conversation_id, "resolved", messages_count=len(messages)))
        return tool_call_result

    # ── 2b. Plain prompt to LLM (no tool step) ───────────────────────
    plain_messages = [
        {
            "role": "system",
            "content": system_block
            + "\n\nAnswer the customer's question using ONLY the context above. "
            + "Be concise. If the context does not contain the answer, say so and offer to escalate.",
        },
        *history_dicts,
    ]

    llm_resp: LLMResponse = call_llm(plain_messages, max_tokens=500)

    if llm_resp.ok:
        cleaned = _clean_reply(llm_resp.content)
        log_ctx["response"] = cleaned
        log_ctx["tokens"] = llm_resp.tokens_used
        _persist_log(log_ctx)
        return Reply(
            text=cleaned,
            tokens_used=llm_resp.tokens_used,
            raw=llm_resp.raw,
        )

    # ── 3. LLM failed — fall back gracefully ───────────────────────
    fallback = (
        "I am having trouble answering that right now. The team can help directly "
        "at styxproxy.com/contact or support@styxproxy.com. I'll let them know you "
        "asked if you'd like."
    )
    log_ctx["response"] = fallback
    log_ctx["error"] = llm_resp.error
    log_ctx["escalated"] = True
    _persist_log(log_ctx)
    
    # Persist assistant message (fallback)
    await _persist_message(conversation_id, channel, "assistant", fallback, tokens_used=0)
    
    return Reply(text=fallback, escalated=True, error=llm_resp.error)


def _run_scenario(scenario: scenarios.Scenario, messages: list[Message], *, conversation_id: str | None = None, customer_email: str | None = None, customer_phone: str | None = None, customer_message: str = "", history_summary: str = "") -> tuple[Any, bool]:
    """Execute a matched scenario's actions. Returns (reply, escalated)."""
    tx_ref = _extract_tx_ref(messages)
    escalated = False
    reply_text = ""
    for action in scenario.actions:
        if action.type == "reply" and action.text:
            if "{{tx_ref_or_unknown}}" in (action.text or ""):
                action.text = action.text.replace("{{tx_ref_or_unknown}}", tx_ref or "unknown")
            reply_text = action.text or ""
        elif action.type == "escalate":
            escalated = True
            _emit_escalation(scenario, action, tx_ref, conversation_id=conversation_id, customer_email=customer_email, customer_phone=customer_phone, customer_message=customer_message, history_summary=history_summary)
        elif action.type == "tool":
            # future: schedule tool call
            pass
    if not reply_text:
        reply_text = (
            "I am not sure I can answer that automatically. The team can help at "
            "styxproxy.com/contact or support@styxproxy.com."
        )
    return type("R", (), {"text": reply_text})(), escalated


def _emit_escalation(
    scenario: scenarios.Scenario,
    action,
    tx_ref: str | None,
    conversation_id: str | None = None,
    customer_email: str | None = None,
    customer_phone: str | None = None,
    customer_message: str = "",
    history_summary: str = "",
) -> None:
    """Persist an escalation record and surface to operator alert hooks."""
    from app.services.charon.escalation_persist import persist_escalation_sync
    summary = (action.summary_template or f"Charon escalated case: {scenario.name}").replace(
        "{{tx_ref_or_unknown}}", tx_ref or "unknown"
    )
    record = {
        "event": "charon.escalation",
        "scenario_id": scenario.id,
        "summary": summary,
        "tx_ref": tx_ref,
        "reason": action.reason,
    }
    logger.warning(json.dumps(record))

    # Persist to DB (background thread — never blocks the reply)
    if conversation_id:
        persist_escalation_sync(
            conversation_id=conversation_id,
            customer_email=customer_email,
            customer_phone=customer_phone,
            customer_message=customer_message,
            history_summary=history_summary,
            scenario_id=scenario.id,
            reason=action.reason,
        )

    # Capture escalation in Sentry for alerting
    sentry_sdk.capture_message(
        f"[Charon Escalation] {scenario.id}: {summary}",
        level="info",
        extras={
            "scenario_id": scenario.id,
            "tx_ref": tx_ref or "none",
            "reason": action.reason or "customer_requested",
        },
    )



async def _try_tool_call(
    *,
    channel: str,
    messages: list[dict],
    extra_system: str,
    user_message: str,
    tx_ref: str | None,
    log_ctx: dict,
):
    """Send the LLM a tool-specs prompt. If a tool returns useful data
    AND the LLM uses it, we wrap that into a reply.

    Returns a Reply if a tool was called and we have a synthesized
    message; returns None if the LLM didn't call a tool (in which case
    the plain-prompt path runs)."""
    # Build a permissive prompt: ask the model to either call a tool
    # by responding with JSON {"tool": "...", "params": {...}} or to
    # answer directly.
    tool_prompt_messages = [
        {
            "role": "system",
            "content": (
                extra_system + "\n\n" + "Format your response strictly as JSON with one of these shapes:\n"
                '{"answer": "<short customer-facing message>"}\n'
                '{"tool": "<tool_name>", "params": {<json-args>}}\n'
                'Pick at most one tool call. If you don\'t need a tool, return {"answer": ...}.'
            ),
        },
        *messages,
    ]

    llm_resp = call_llm(tool_prompt_messages, max_tokens=400)
    if not llm_resp.ok:
        return None
    log_ctx["tokens"] = log_ctx.get("tokens", 0) + llm_resp.tokens_used

    parsed = _safe_parse_tool_json(llm_resp.content)
    if parsed is None:
        return None

    if "tool" in parsed and isinstance(parsed["tool"], str):
        tool_name = parsed["tool"]
        tool_params = parsed.get("params") or {}
        if tool_name in (tools.registry.tools.keys()):
            log_ctx.setdefault("tool_calls", []).append(
                {
                    "tool": tool_name,
                    "params": tool_params,
                }
            )
            result = await tools.registry.call(tool_name, **tool_params)
            if result.ok:
                # Compose a follow-up prompt with the tool result so
                # the LLM can synthesise a customer-facing answer.
                follow_up_messages = [
                    {
                        "role": "system",
                        "content": (
                            extra_system
                            + "\n\nYou called a tool. Here is its result:\n"
                            + json.dumps(result.data, default=str)
                            + "\n\nCompose a 1–3 sentence customer-facing answer based ONLY on this. Be concise."
                        ),
                    },
                    *messages,
                ]
                follow_up = call_llm(follow_up_messages, max_tokens=400)
                if follow_up.ok:
                    log_ctx["tokens"] = log_ctx.get("tokens", 0) + follow_up.tokens_used
                    return Reply(
                        text=_clean_reply(follow_up.content),
                        tool_calls=[{"tool": tool_name, "params": tool_params, "result": result.to_dict()}],
                        tokens_used=log_ctx.get("tokens", 0),
                    )
            else:
                # tool failure → escalate — capture in Sentry
                sentry_sdk.capture_message(
                    f"[Charon Tool Error] {tool_name}: {result.error}",
                    level="warning",
                    extras={
                        "tool": tool_name,
                        "params": tool_params,
                        "error": result.error or "unknown",
                    },
                )
                return Reply(
                    text=(
                        "I cannot complete this step automatically right now. Let me escalate so the team "
                        "can help at styxproxy.com/contact or support@styxproxy.com."
                    ),
                    tool_calls=[{"tool": tool_name, "params": tool_params, "error": result.error}],
                    escalated=True,
                    error=result.error,
                )
        else:
            # LLM hallucinated a tool name we don't have
            return None

    if "answer" in parsed:
        return Reply(text=_clean_reply(str(parsed["answer"])))

    return None


def _safe_parse_tool_json(content: str) -> dict | None:
    """Pull a JSON object out of the model's response. Tolerate
    markdown code fences and stray prose."""
    text = content.strip()
    # strip ```json fences
    if text.startswith("```"):
        lines = [item for item in text.splitlines() if not item.strip().startswith("```")]
        text = "\n".join(lines).strip()
    # try direct parse
    try:
        return json.loads(text)
    except (ValueError, json.JSONDecodeError):
        pass
    # find first {...} block
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = text[start : end + 1]
        try:
            return json.loads(candidate)
        except (ValueError, json.JSONDecodeError):
            return None
    return None


def _persist_log(ctx: dict) -> None:
    """Best-effort persistence to logs/charon.log as JSONL.

    When a real database is wired (Postgres on Railway), this gets
    replaced with an INSERT into charon_logs. Until then, a flat
    JSONL file gives us grep-ability and lets the operation team
    read today's escalation list with `tail -f logs/charon.log`.
    """
    log_dir = os.getenv("CHARON_LOG_DIR", "/tmp")
    log_path = os.path.join(log_dir, "charon.log")  # nosec B108
    try:
        os.makedirs(log_dir, exist_ok=True)
        with open(log_path, "a") as fh:
            fh.write(json.dumps({"ts": datetime.now(timezone.utc).isoformat(), **ctx}) + "\n")
    except OSError:
        pass  # best-effort
    logger.info("charon.reply", extra={"charon": ctx})


async def _persist_message(
    conversation_id: str,
    channel: str,
    role: str,
    content: str,
    tool_calls: list[dict] | None = None,
    tokens_used: int = 0,
    page_context: dict | None = None,
) -> None:
    """Persist a message to the charon_conversations/charon_messages tables."""
    try:
        from datetime import datetime, timezone
        from app.database import async_session
        from app.models import CharonConversation, CharonMessage
        from sqlalchemy import select
        
        async with async_session() as session:
            # Find or create conversation
            stmt = select(CharonConversation).where(CharonConversation.session_id == conversation_id)
            result = await session.execute(stmt)
            conv = result.scalar_one_or_none()
            
            if not conv:
                conv = CharonConversation(
                    session_id=conversation_id,
                    channel=channel,
                    page_context=page_context,
                )
                session.add(conv)
                await session.flush()
            
            # Create message
            msg = CharonMessage(
                conversation_id=conv.id,
                role=role,
                content=content,
                tool_calls=tool_calls,
                tokens_used=tokens_used,
            )
            session.add(msg)
            
            # Update conversation stats
            conv.message_count += 1
            conv.last_activity_at = datetime.now(timezone.utc)
            if tokens_used:
                conv.tokens_used += tokens_used
            if role == "user" and page_context:
                conv.page_context = page_context
            
            await session.commit()
    except Exception as exc:
        logger.warning("Failed to persist message: %s", exc)


async def _load_context_summary(conversation_id: str) -> str | None:
    """Load the rolling context summary for a conversation."""
    try:
        from app.database import async_session
        from app.models import CharonContext
        from sqlalchemy import select
        
        async with async_session() as session:
            stmt = select(CharonContext).where(
                CharonContext.conversation_id == conversation_id,
                CharonContext.expires_at > datetime.now(timezone.utc),
            )
            result = await session.execute(stmt)
            ctx = result.scalar_one_or_none()
            return ctx.summary_json if ctx else None
    except Exception:
        return None


async def _save_context_summary(
    conversation_id: str,
    summary: str,
    message_count: int,
    last_intent: str | None = None,
    last_topics: list[str] | None = None,
    customer_email: str | None = None,
    customer_phone: str | None = None,
) -> None:
    """Save or update the rolling context summary for a conversation."""
    try:
        from datetime import datetime, timezone, timedelta
        from app.database import async_session
        from app.models import CharonContext
        from sqlalchemy import select
        
        async with async_session() as session:
            stmt = select(CharonContext).where(CharonContext.conversation_id == conversation_id)
            result = await session.execute(stmt)
            ctx = result.scalar_one_or_none()
            
            if ctx:
                ctx.summary_json = summary
                ctx.message_count = message_count
                ctx.last_intent = last_intent
                ctx.last_topics = last_topics
                ctx.updated_at = datetime.now(timezone.utc)
                ctx.expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
            else:
                ctx = CharonContext(
                    conversation_id=conversation_id,
                    summary_json=summary,
                    message_count=message_count,
                    last_intent=last_intent,
                    last_topics=last_topics,
                    customer_email=customer_email,
                    customer_phone=customer_phone,
                    expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
                )
                session.add(ctx)
            
            await session.commit()
    except Exception as exc:
        logger.warning("Failed to save context summary: %s", exc)
