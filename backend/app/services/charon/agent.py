"""Charon agent orchestrator — smarter, sales-oriented, context-aware."""
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
    r"\b(?:STX|TX|TXF|TXF-ORD|ORD)-\d{4,}[A-Z0-9\-]*|\b[A-Z0-9]{6,12}-\d{4,}\b",
    re.IGNORECASE,
)

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
_FENCED_CODE = re.compile(r"```[a-zA-Z0-9_+\-]*?\n.*?```", re.DOTALL)
_TABLE_ROW = re.compile(r"^\s*\|.*\|\s*$", re.MULTILINE)
_TABLE_SEPARATOR = re.compile(r"^\s*\|?[\s:\-|]+\|?\s*$", re.MULTILINE)
_BLANK_RUN = re.compile(r"\n{3,}")


def _clean_reply(text: str) -> str:
    if not text:
        return text
    out = text
    for pat in _THINK_BLOCKS:
        out = pat.sub("", out)
    out = _FENCED_CODE.sub("", out)
    lines = out.splitlines()
    cleaned: list[str] = []
    table_buf: list[str] = []

    def flush_table() -> None:
        if not table_buf:
            return
        rows: list[list[str]] = []
        for row in table_buf:
            if _TABLE_SEPARATOR.match(row):
                continue
            cells = [c.strip() for c in row.strip().strip("|").split("|")]
            rows.append(cells)
        if not rows:
            table_buf.clear()
            return
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


async def _load_history_from_db(conversation_id: str, limit: int = 8) -> list[Message]:
    """Load recent conversation history from database."""
    try:
        from app.database import async_session
        from app.models import CharonMessage
        from sqlalchemy import select

        async with async_session() as session:
            stmt = (
                select(CharonMessage)
                .where(CharonMessage.conversation_id == conversation_id)
                .order_by(CharonMessage.ts.desc())
                .limit(limit)
            )
            result = await session.execute(stmt)
            messages = result.scalars().all()
            return [Message(role=m.role, content=m.content) for m in reversed(messages)]
    except Exception:
        return []


# ─── Domain Knowledge (injected into system prompt) ─────────────────────────

DOMAIN_KNOWLEDGE = """
## Proxy Domain Knowledge

### Plan Types & When to Use Each

**Residential Proxies** 🇳🇬🇺🇸🇬🇧
- Real home IPs assigned to real subscribers
- Hardest to detect and block
- Price: per GB (5GB ₦5,000 → 50GB ₦80,000)
- Best for: social media management, ad verification, market research, sneaker bots
- Streaming services and social platforms have lowest friction with residential

**Mobile 4G Proxies** 📱
- Real mobile carrier IPs
- Highest trust score for platforms because carrier subscriber traffic is well represented
- Price: per GB (5GB ₦25,000 → 10GB ₦45,000)
- Best for: account creation, social platforms that fingerprint mobile, ad verification
- Most expensive but lowest detection rate

**ISP Proxies** 🏢
- Datacenter IPs registered to real Internet Service Providers
- Fast + residential-like reputation
- Price: per IP/month (from ₦6,500)
- Best for: web scraping, automation, account creation, sneaker sites
- Balance of speed and trust — static IP for your subscription period

**Datacenter Proxies** 🖥️
- Bare-metal server IPs — fastest, cheapest, easiest to detect
- Price: per IP/month (10 IPs ₦3,000 → 100 IPs ₦20,000)
- Best for: large-scale scraping, SEO monitoring, price aggregation, server testing
- Not recommended for streaming or social media — easily blocked

### Payment Methods
- **Card** (Visa, Mastercard) — instant delivery
- **USSD** — instant delivery (Nigerian banks)
- **Bank transfer** — few minutes longer
- **QR code** — instant
- Crypto NOT accepted (public ledger defeats anonymity purpose)

### Common Use Cases → Plan Recommendations
- Instagram/TikTok management → Residential or Mobile
- Twitter automation → Residential or ISP
- Ad verification → Mobile (highest trust)
- Sneaker bots → Residential or ISP
- Web scraping (large scale) → Datacenter
- SEO monitoring → Datacenter
- Streaming services → Residential (never datacenter)
- Account creation on strict platforms → Mobile
- Price comparison → Datacenter

### Setup Quick Reference
- Proxy address: `proxy.styxproxy.com:PORT`
- Auth: Styxproxy username + password
- Protocols: HTTP, HTTPS, SOCKS5 all supported
- Test proxy: visit https://ipinfo.io to confirm it's active
- Sticky sessions: available on residential (same IP for 5-30 min)
- Static IPs: ISP and Datacenter plans
"""

# ─── Sales Intelligence ─────────────────────────────────────────────────────

SALES_INTELLIGENCE = """
## Sales Mode Active

You are in **sales mode** on a messaging app. Your goal is to help customers buy — not just answer questions.

### Buying Signals (watch for these)
- "I want to buy", "I need a proxy", "get me", "set me up"
- "How much for X" → immediately quote + offer to create order
- "Which plan is best for X" → recommend + offer to set up
- "Do you have X country" → check catalog + offer order
- Customer asks about pricing → give exact price + "Want me to create that order?"

### Sales Flow
1. **Identify need**: What are they trying to do? (scraping, social media, streaming)
2. **Recommend plan**: Match use case to plan type + country
3. **Create order**: Use `create_order` with channel_user_id from context
4. **Drive payment**: Use `initiate_payment` + give checkout link clearly
5. **Confirm delivery**: After payment, credentials appear automatically

### Upsell & Cross-Sell
- Customer buying datacenter → "Need residential for trickier sites? Only ₦X more"
- Customer buying 5GB → "10GB is ₦X (2x the data, better per-GB rate)"
- Customer buying single IP → "10 IPs is ₦X — enough for a small team"
- New customer → "First order? Residential is our most popular starting point"

### Objection Handling
- "Too expensive" → "Datacenter is cheaper per IP if you don't need stealth"
- "I'm not sure" → "What are you trying to do? I'll recommend the best fit"
- "Let me think" → "Sure — here's the pricing again. When you're ready, just tell me the plan."

### Proactive Next Steps
After EVERY answer, suggest a relevant next step:
- After explaining a plan → "Want me to create that order?"
- After troubleshooting → "Need a fresh proxy? I can set that up"
- After order lookup → "Need to renew? I can help with that"
- After payment → "Your proxy will be ready in minutes. Want setup instructions?"

### Charon Capabilities (when asked "what can you do")
"I can help you with:
- 📋 **Browse plans** — show all proxy types, prices, and countries
- 🔍 **Compare plans** — side-by-side differences and recommendations
- 🛒 **Create orders** — set up your proxy in seconds
- 💳 **Payment** — checkout link, retry failed payments
- 📦 **Order lookup** — status, credentials, history
- 📊 **Data usage** — check remaining GB on residential/mobile
- 🔄 **Renewals** — expiring soon? Renew now
- 🛠️ **Setup guides** — how to configure any plan
- 🐛 **Troubleshooting** — common issues and fixes
- 👥 **Referrals** — earn ₦500 for each friend you refer
- 🏢 **Bulk pricing** — custom quotes for 20+ IPs
- 💻 **Integration docs** — code examples for Python, Node, Selenium, etc."
"""

# ─── Customer Context Awareness ─────────────────────────────────────────────

async def _get_customer_context_summary(customer_phone: str | None) -> str:
    """Call get_customer_context tool and format for system prompt."""
    if not customer_phone:
        return ""
    try:
        result = await tools.registry.call("get_customer_context", customer_phone=customer_phone)
        if not result.ok:
            return ""
        data = result.data
        if data.get("is_new_customer"):
            return "\n## Customer Context\nNew customer — no purchase history yet. Be welcoming, explain options.\n"
        
        tier = data.get("tier", "new")
        tier_note = ""
        if tier == "vip":
            tier_note = " ⭐ VIP CUSTOMER — prioritize, offer best recommendations, thank them for loyalty"
        elif tier == "returning":
            tier_note = " 🔁 Returning customer — acknowledge their history"
        
        recent = data.get("recent_orders", [])
        recent_str = ""
        if recent:
            recent_str = "\nRecent orders:\n" + "\n".join(
                f"  • {o.get('plan_type', '?')} ({o.get('plan_code', '?')}) — {o.get('status', '?')} — ₦{o.get('amount', 0):,.0f}"
                for o in recent[:3]
            )
        
        creds = data.get("active_credentials", [])
        creds_str = ""
        if creds:
            creds_str = f"\nActive credentials: {len(creds)} proxy(ies) running"
        
        # Check for expiring proxies
        expiring_str = ""
        try:
            from app.services.charon import tools as _tools
            renew_result = await _tools.registry.call("detect_renewal", customer_phone=customer_phone)
            if renew_result.ok and renew_result.data.get("expiring_soon"):
                n = len(renew_result.data["expiring_soon"])
                expiring_str = f"\n⚠️ {n} proxy expiring within 7 days"
        except Exception:
            pass
        
        # Check data remaining for residential/mobile customers
        data_str = ""
        try:
            from app.services.charon import tools as _tools2
            data_result = await _tools2.registry.call("check_data_remaining", customer_phone=customer_phone)
            if data_result.ok and data_result.data.get("active_data_plans"):
                total_rem = data_result.data.get("total_remaining_gb", 0)
                total_alloc = data_result.data.get("total_allocated_gb", 0)
                if total_alloc > 0:
                    pct = round(total_rem / total_alloc * 100, 1)
                    data_str = f"\n📊 Data remaining: {total_rem:.1f}GB / {total_alloc:.1f}GB ({pct}%)"
        except Exception:
            pass
        
        return (
            f"\n## Customer Context{tier_note}\n"
            f"Name: {data.get('customer_name', 'Customer')}\n"
            f"Tier: {tier}\n"
            f"Total orders: {data.get('total_orders', 0)}\n"
            f"Total spend: ₦{data.get('total_spend_ngn', 0):,.0f}\n"
            f"Last order: {data.get('last_order_at', 'never')}"
            f"{recent_str}"
            f"{creds_str}"
            f"{data_str}"
            f"{expiring_str}"
            + "\n"
        )
    except Exception as exc:
        logger.warning("Failed to get customer context: %s", exc)
        return ""


async def reply(
    channel: str,
    conversation_id: str,
    user_message: str,
    *,
    history: list[Message] | None = None,
    page_context: dict | None = None,
    channel_user_id: str | None = None,
    customer_phone: str | None = None,
    customer_name: str | None = None,
) -> Reply:
    """End-to-end Charon reply."""
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

    # Load history from DB if not provided by caller
    if history is None and conversation_id:
        history = await _load_history_from_db(conversation_id, limit=8)

    messages = list(history or [])
    messages.append(Message(role="user", content=user_message))

    # ── 0. Conversation timeout ──────────────────────────────────────
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
    MAX_TOKENS_PER_CONVERSATION = 8000
    history_tokens = sum(len(m.content or "") for m in messages) // 4
    if history_tokens > MAX_TOKENS_PER_CONVERSATION:
        return Reply(
            text="I've spent a lot of time on this. Let me escalate to the team for better help.",
            escalated=True,
            error="conversation_budget_exhausted",
        )

    # ── 2. LLM with knowledge + tools ──────────────────────────────
    context_chunks = knowledge.search(user_message, top_k=4)
    context_text = knowledge.format_context(context_chunks)
    
    context_summary = await _load_context_summary(conversation_id)
    if context_summary:
        context_text = f"Previous conversation summary:\n{context_summary}\n\n{context_text}"

    tx_ref = _extract_tx_ref(messages)
    history_dicts = _serialize_history(messages[-8:])

    filtered_context, _ = get_page_context_variant(conversation_id, page_context)
    page_prompt = get_page_prompt_addition(filtered_context)

    # ── NEW: Customer context for personalization ───────────────────
    customer_ctx = await _get_customer_context_summary(customer_phone)
    
    # Charon personality + formatting (compact)
    personality_block = (
        "\n\n"
        "## Your Personality\n"
        "You are **Charon** — Styxproxy's customer-facing AI assistant.\n"
        "- Warm, proactive, honest. Like a knowledgeable friend who knows proxies.\n"
        "- Never robotic: no 'Certainly!', 'As an AI...', 'I'd be happy to assist!'\n"
        "- Use emojis naturally: 🎉 ✅ 💡 🔒 📦 🚀\n\n"
        "## Formatting\n"
        "- **Bold** for key info (prices, plan names, order IDs)\n"
        "- [links](url) for URLs\n"
        "- Bullet points for lists\n"
        "- Short paragraphs (1-2 sentences)\n"
        "- End with a question or next-step suggestion\n\n"
        "## Country Flags\n"
        "Use flag emojis, not codes: 🇳🇬 Nigeria, 🇺🇸 US, 🇬🇧 UK, 🇩🇪 Germany, 🇨🇳 China, 🇦🇪 UAE, 🇬🇭 Ghana, 🇧🇷 Brazil, 🇧🇪 Belgium, 🇦🇫 Afghanistan, 🇦🇷 Argentina. If unsure, write the full name.\n"
    )

    # Sales-specific additions for chat channels
    sales_prompt = ""
    if channel in ("telegram", "whatsapp"):
        sales_prompt = SALES_INTELLIGENCE

    system_block = (
        "You may use these tools if relevant. Call them only when useful; "
        "you do not need to call a tool to answer. Tools are read-only unless otherwise noted. "
        "If the customer asks for a mutation (refund, replacement, cancellation), you must "
        "decline and offer to escalate. Use suggest_articles or "
        "get_product_catalog before guessing.\n\n"
        f"Available tools:\n{json.dumps(tools.registry.list_specs(), indent=2)}\n\n"
        f"Known transaction reference (if any): {tx_ref or 'none mentioned yet'}\n\n"
        f"Knowledge base context:\n{context_text}\n"
        + (f"\n\n{page_prompt}" if page_prompt else "")
        + (f"\n\n{DOMAIN_KNOWLEDGE}" if channel in ("telegram", "whatsapp", "web") else "")
        + sales_prompt
        + personality_block
        + customer_ctx
    )

    # Store channel_user_id in context for tool calls
    if channel_user_id:
        system_block += f"\n\nChannel user ID (for create_order): {channel_user_id}"

    # ── 2a. Try a tool-calling loop (multi-step) ────────────────────
    tool_call_result = await _try_tool_call_loop(
        channel=channel,
        messages=history_dicts,
        extra_system=system_block,
        user_message=user_message,
        tx_ref=tx_ref,
        log_ctx=log_ctx,
        channel_user_id=channel_user_id,
        customer_phone=customer_phone,
        customer_name=customer_name,
    )
    if tool_call_result is not None:
        log_ctx["response"] = tool_call_result.text
        _persist_log(log_ctx)
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
    
    await _persist_message(conversation_id, channel, "assistant", fallback, tokens_used=0)
    
    return Reply(text=fallback, escalated=True, error=llm_resp.error)


def _run_scenario(scenario: scenarios.Scenario, messages: list[Message], *, conversation_id: str | None = None, customer_email: str | None = None, customer_phone: str | None = None, customer_message: str = "", history_summary: str = "") -> tuple[Any, bool]:
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

    sentry_sdk.capture_message(
        f"[Charon Escalation] {scenario.id}: {summary}",
        level="info",
        extras={
            "scenario_id": scenario.id,
            "tx_ref": tx_ref or "none",
            "reason": action.reason or "customer_requested",
        },
    )


async def _try_tool_call_loop(
    *,
    channel: str,
    messages: list[dict],
    extra_system: str,
    user_message: str,
    tx_ref: str | None,
    log_ctx: dict,
    channel_user_id: str | None = None,
    customer_phone: str | None = None,
    customer_name: str | None = None,
    max_iterations: int = 3,
):
    """Multi-step tool calling loop."""
    tool_prompt_messages = [
        {
            "role": "system",
            "content": (
                extra_system + "\n\n" + "CRITICAL: Output ONLY raw JSON. No XML. No markdown. No explanations.\n\n"
                "Valid formats (pick ONE):\n"
                '{"answer": "<customer message>"}\n'
                '{"tool": "<tool_name>", "params": {...}}\n\n'
                "INVALID (never do this):\n"
                "- <tool_call>...</tool_call>\n"
                "- ```json ... ```\n"
                "- Here is my response: ...\n"
                "- Any text outside the JSON\n\n"
                "If you need a tool, output ONLY: {\"tool\": \"name\", \"params\": {...}}\n"
                "If answering directly, output ONLY: {\"answer\": \"message\"}\n"
            ),
        },
        *messages,
    ]

    all_tool_calls: list[dict] = []
    total_tokens = 0

    for iteration in range(max_iterations):
        llm_resp = call_llm(tool_prompt_messages, max_tokens=400)
        if not llm_resp.ok:
            return None
        total_tokens += llm_resp.tokens_used

        parsed = _safe_parse_tool_json(llm_resp.content)
        if parsed is None:
            return None

        if "tool" in parsed and isinstance(parsed["tool"], str):
            tool_name = parsed["tool"]
            tool_params = parsed.get("params") or {}

            # Inject channel_user_id and channel for create_order
            if tool_name == "create_order":
                if channel_user_id and "channel_user_id" not in tool_params:
                    tool_params["channel_user_id"] = channel_user_id
                if channel and "channel" not in tool_params:
                    tool_params["channel"] = channel
                if customer_name and "customer_name" not in tool_params:
                    tool_params["customer_name"] = customer_name

            # Inject customer_phone for read tools (RLS context)
            if tool_name in ("lookup_order", "lookup_payment_status", "generate_order_link", "generate_receipt_link", "get_customer_context", "list_customer_orders", "check_data_remaining", "get_referral_info", "detect_renewal", "escalate_bulk_inquiry"):
                if customer_phone and "customer_phone" not in tool_params:
                    tool_params["customer_phone"] = customer_phone

            if tool_name not in tools.registry.tools:
                return None

            log_ctx.setdefault("tool_calls", []).append(
                {"tool": tool_name, "params": tool_params}
            )
            result = await tools.registry.call(tool_name, **tool_params)

            if result.ok:
                all_tool_calls.append({"tool": tool_name, "params": tool_params, "result": result.to_dict()})

                # Add tool result to conversation and continue loop
                tool_prompt_messages.append({
                    "role": "assistant",
                    "content": json.dumps({"tool": tool_name, "params": tool_params}),
                })
                tool_prompt_messages.append({
                    "role": "user",
                    "content": f"Tool result: {json.dumps(result.data, default=str)}\n\n"
                               f"If you need to call another tool, respond with {{'tool': '...', 'params': {{...}}}}. "
                               f"Otherwise, respond with {{'answer': '<customer-facing message>'}} based on the results so far.",
                })
            else:
                sentry_sdk.capture_message(
                    f"[Charon Tool Error] {tool_name}: {result.error}",
                    level="warning",
                    extras={"tool": tool_name, "params": tool_params, "error": result.error or "unknown"},
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
        elif "answer" in parsed:
            # LLM has decided to answer — synthesize final response
            follow_up_messages = [
                {
                    "role": "system",
                    "content": (
                        extra_system
                        + "\n\nYou have completed the following tool calls:\n"
                        + json.dumps(all_tool_calls, default=str)
                        + "\n\nCompose a 1–3 sentence customer-facing answer based ONLY on these results. Be concise."
                    ),
                },
                *messages,
            ]
            follow_up = call_llm(follow_up_messages, max_tokens=400)
            if follow_up.ok:
                total_tokens += follow_up.tokens_used
                return Reply(
                    text=_clean_reply(follow_up.content),
                    tool_calls=all_tool_calls,
                    tokens_used=total_tokens,
                )
            else:
                return Reply(
                    text=_clean_reply(str(parsed["answer"])),
                    tool_calls=all_tool_calls,
                    tokens_used=total_tokens,
                )
        else:
            return None

    # If we exhausted iterations, synthesize what we have
    if all_tool_calls:
        follow_up_messages = [
            {
                "role": "system",
                "content": (
                    extra_system
                    + "\n\nYou have completed the following tool calls:\n"
                    + json.dumps(all_tool_calls, default=str)
                    + "\n\nCompose a 1–3 sentence customer-facing answer based ONLY on these results. Be concise."
                ),
            },
            *messages,
        ]
        follow_up = call_llm(follow_up_messages, max_tokens=400)
        if follow_up.ok:
            total_tokens += follow_up.tokens_used
            return Reply(
                text=_clean_reply(follow_up.content),
                tool_calls=all_tool_calls,
                tokens_used=total_tokens,
            )

    return None


def _safe_parse_tool_json(content: str) -> dict | None:
    import re as _re
    text = content.strip()
    # Handle <tool_call>...</tool_call> XML format
    for match in _re.finditer(r'<tool_call>(.*?)</tool_call>', text, _re.DOTALL):
        inner = match.group(1).strip()
        try:
            parsed = json.loads(inner)
            if 'tool_name' in parsed:
                return {'tool': parsed['tool_name'], 'params': parsed.get('arguments', {})}
            if 'name' in parsed:
                return {'tool': parsed['name'], 'params': parsed.get('arguments', {})}
            if 'tool' in parsed:
                return parsed
            return parsed
        except (ValueError, json.JSONDecodeError):
            start = inner.find('{')
            end = inner.rfind('}')
            if start != -1 and end != -1 and end > start:
                try:
                    parsed = json.loads(inner[start:end+1])
                    if 'tool_name' in parsed:
                        return {'tool': parsed['tool_name'], 'params': parsed.get('arguments', {})}
                    if 'name' in parsed:
                        return {'tool': parsed['name'], 'params': parsed.get('arguments', {})}
                    return parsed
                except (ValueError, json.JSONDecodeError):
                    pass
    if text.startswith("```"):
        lines = [item for item in text.splitlines() if not item.strip().startswith("```")]
        text = "\n".join(lines).strip()
    try:
        return json.loads(text)
    except (ValueError, json.JSONDecodeError):
        pass
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
    log_dir = os.getenv("CHARON_LOG_DIR", "/tmp")
    log_path = os.path.join(log_dir, "charon.log")
    try:
        os.makedirs(log_dir, exist_ok=True)
        with open(log_path, "a") as fh:
            fh.write(json.dumps({"ts": datetime.now(timezone.utc).isoformat(), **ctx}) + "\n")
    except OSError:
        pass
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
    try:
        from datetime import datetime, timezone
        from app.database import async_session
        from app.models import CharonConversation, CharonMessage
        from sqlalchemy import select
        
        async with async_session() as session:
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
            
            msg = CharonMessage(
                conversation_id=conv.id,
                role=role,
                content=content,
                tool_calls=tool_calls,
                tokens_used=tokens_used,
            )
            session.add(msg)
            
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
