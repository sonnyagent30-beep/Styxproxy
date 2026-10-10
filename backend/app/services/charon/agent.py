"""Charon agent orchestrator — smarter, sales-oriented, context-aware."""
from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime, timezone, timedelta
import re
import uuid
from dataclasses import dataclass, field
from typing import Any, Iterable

import sentry_sdk

from app.services.charon.page_templates import get_page_prompt_addition
from app.services.charon.ab_framework import get_variant, get_page_context_variant, record_outcome
from app.services.charon.credential_guard import inspect_text, redact_mapping
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
    interrupted: bool = False


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
_BLANK_RUN = re.compile(r"\n{3,}")

# ─── Tool Call Stripper (A3) ──────────────────────────────────────────────────
# Known tool names from the registry. Used to detect malformed tool calls
# that leak internal tool names to customers.
_KNOWN_TOOL_NAMES = [
    "get_product_catalog", "lookup_order", "list_customer_orders",
    "check_data_remaining", "detect_renewal", "get_referral_info",
    "get_setup_guide", "get_troubleshooting", "create_order",
    "initiate_payment", "retry_payment", "escalate_bulk_inquiry",
    "compare_plans", "generate_order_link", "generate_receipt_link",
    "get_customer_context", "check_order_status", "check_proxy_status",
    "check_delivery_status", "lookup_order_by_email", "lookup_payment_status",
    "initiate_renewal", "suggest_articles",
]

_TOOL_NAME_RE = "|".join(re.escape(name) for name in _KNOWN_TOOL_NAMES)

# Well-formed: <tool_name>\n...content</tool_name>
_LONGCAT_TOOL_CALL = re.compile(
    r"<(" + _TOOL_NAME_RE + r")>\s*\n.*?</\1>",
    re.DOTALL | re.IGNORECASE
)

# Any tag containing a tool name (opening or closing, malformed)
_LONGCAT_TOOL_CALL_TAGS = re.compile(
    r"</?(" + _TOOL_NAME_RE + r")>",
    re.IGNORECASE
)

# Bare tool name followed by non-ASCII-word or non-space (e.g. get_product_catalog立卡).
# Uses explicit ASCII character classes instead of \b, which is Unicode-aware in
# Python 3 and treats CJK characters as word characters (so catalog立卡 = one word).
_LONGCAT_TOOL_CALL_BARE = re.compile(
    r"(?<![a-zA-Z0-9_])(" + _TOOL_NAME_RE + r")(?![a-zA-Z0-9_])",
    re.IGNORECASE
)

# Any closing tag that is NOT a known HTML tag (catches </th>, </table>, etc.)
_HTML_TAGS = frozenset([
    "b", "i", "em", "strong", "code", "pre", "p", "br", "hr", "div", "span",
    "a", "ul", "ol", "li", "h1", "h2", "h3", "h4", "h5", "h6", "blockquote",
])

_LONGCAT_TOOL_CALL_CLOSE_GENERAL = re.compile(
    r"</(\w+)>",
    re.IGNORECASE
)


def _strip_tool_calls(text: str) -> str:
    """Strip tool call artifacts from customer-facing text.

    Runs on EVERY response path. The model emits malformed tool calls that
    leak internal tool names (observed: get_product_catalog立卡 / ...</th>).
    This function catches all forms and replaces them with a status affordance.
    """
    if not text:
        return text
    # Well-formed: <tool_name>\n...</tool_name>
    text = _LONGCAT_TOOL_CALL.sub(" Looking up plans\u2026 ", text)
    # Any tag containing a tool name
    text = _LONGCAT_TOOL_CALL_TAGS.sub(" Looking up plans\u2026 ", text)
    # Bare tool name followed by non-word, non-space
    text = _LONGCAT_TOOL_CALL_BARE.sub(" Looking up plans\u2026 ", text)
    # Any closing tag that is not a known HTML tag
    def _replace_close(match):
        tag = match.group(1).lower()
        if tag in _HTML_TAGS:
            return match.group(0)
        return " Looking up plans\u2026 "
    text = _LONGCAT_TOOL_CALL_CLOSE_GENERAL.sub(_replace_close, text)
    return text


def _clean_reply(text: str) -> str:
    if not text:
        return text
    out = text
    for pat in _THINK_BLOCKS:
        out = pat.sub("", out)
    # A3: Run tool-call stripper on EVERY path
    out = _strip_tool_calls(out)
    out = _FENCED_CODE.sub("", out)
    # A4: Let markdown tables through — do NOT flatten them.
    # The frontend (ReactMarkdown + remarkGfm) renders tables natively.
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
- Proxy address: `YOUR_PROXY_IP:PORT`
- Auth: Styxproxy username + password
- Protocols: HTTP, HTTPS, SOCKS5 all supported
- Test proxy: visit https://ipinfo.io to confirm it's active
- Sticky sessions: available on residential (same IP for 5-30 min)
- Static IPs: ISP and Datacenter plans

### Renewal Flow
When a customer wants to renew their proxy:
1. Identify the customer (by phone/email from channel context)
2. Use `list_customer_orders` to show their proxies, or `detect_renewal` to find expiring ones
3. Ask which proxy they want to renew and how much data (min 5 GB for residential/mobile)
4. Use `initiate_renewal` with the order_id and quantity_gb
5. Give them the checkout URL and confirm the renewal details
6. After payment, the renewal is processed automatically — same IP if available, new expiry from renewal date

Renewal rules:
- Residential/mobile: customer selects GB amount (5, 10, 20, 50 GB tiers or custom, min 5 GB)
- DC/ISP: no GB selection, just extends expiry by 30 days
- Renewals stack from the renewal date (not current expiry)
- Unlimited renewals per order
- Same IP is kept if still available; otherwise a new one is assigned
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
- After order lookup → "Need to renew? I can help with that — just tell me which proxy and how much data"
- After payment → "Your proxy will be ready in minutes. Want setup instructions?"

### Charon Capabilities (when asked "what can you do")
"I can help you with:
- 📋 **Browse plans** — show all proxy types, prices, and countries
- 🔍 **Compare plans** — side-by-side differences and recommendations
- 🛒 **Create orders** — set up your proxy in seconds
- 💳 **Payment** — checkout link, retry failed payments
- 📦 **Order lookup** — status, credentials, history
- 📊 **Data usage** — check remaining GB on residential/mobile
- 🔄 **Renewals** — expiring soon? I can renew your proxy right here — just tell me which one and how much data
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
    customer_email: str | None = None,
    customer_phone: str | None = None,
    customer_name: str | None = None,
) -> Reply:
    """End-to-end Charon reply."""
    conversation_id = conversation_id or str(uuid.uuid4())
    variant = get_variant(conversation_id)

    # Defence in depth. `app/routers/charon.py` already screens
    # `ChatReplyRequest.user_message` before calling in, and that is the choke
    # point for HTTP traffic. This is the SECOND gate, at the point where the text
    # is provably both persisted and LLM-bound, so a future non-HTTP caller
    # (a proactive trigger, a new router, a script) cannot reintroduce the leak
    # by skipping the router. Redaction is idempotent, so double application is
    # a no-op rather than a double-mangle.
    guard = inspect_text(user_message)
    if guard.has_secret:
        logger.warning(
            "credential_guard: redacted labelled secret value(s) before "
            "persist+LLM: labels=%s conversation_id=%s",
            sorted(guard.secret_labels),
            conversation_id,
        )
        user_message = guard.redacted
    if history:
        history = [
            Message(role=m.role, content=inspect_text(m.content).redacted)
            if m.role in ("user", "assistant")
            else m
            for m in history
        ]
    if page_context:
        page_context = redact_mapping(page_context)

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

    # ── 0b. Inactivity timeout (30 min) ─────────────────────────────
    INACTIVITY_TIMEOUT_MIN = 30
    try:
        from app.database import async_session
        from app.models import CharonConversation
        from sqlalchemy import select

        async with async_session() as session:
            stmt = select(CharonConversation.last_activity_at).where(
                CharonConversation.session_id == conversation_id
            )
            result = await session.execute(stmt)
            last_activity = result.scalar_one_or_none()
            if last_activity:
                now = datetime.now(timezone.utc)
                if last_activity.tzinfo is None:
                    last_activity = last_activity.replace(tzinfo=timezone.utc)
                elapsed = (now - last_activity).total_seconds()
                if elapsed > INACTIVITY_TIMEOUT_MIN * 60:
                    await _save_context_summary(
                        conversation_id=conversation_id,
                        summary="",
                        message_count=0,
                        last_intent=None,
                        last_topics=None,
                        customer_email=customer_email,
                        customer_phone=customer_phone,
                    )
                    messages = [Message(role="user", content=user_message)]
                    history_dicts = []
                    logger.info("Conversation reset due to inactivity (%.0f min)", elapsed / 60)
    except Exception as exc:
        logger.warning("Failed to check inactivity timeout: %s", exc)

    # ── 1. Scenario matcher ──────────────────────────────────────────
    scenario = scenarios.match(user_message)
    if scenario:
        reply_action, escalate = await _run_scenario(scenario, messages, conversation_id=conversation_id, customer_email=customer_email, customer_phone=customer_phone, customer_message=user_message, history_summary="")
        log_ctx["scenario_id"] = scenario.id
        log_ctx["response"] = reply_action.text
        log_ctx["escalated"] = escalate
        _persist_log(log_ctx)
        return Reply(text=reply_action.text, scenario_id=scenario.id, escalated=escalate, experiment_variant=variant.value)

    # ── 1a. Proactive outreach triggers ──────────────────────────────
    proactive_msg = await check_proactive_triggers(
        conversation_id, page_context or {},
        customer_email=customer_email,
        customer_phone=customer_phone,
        customer_name=customer_name,
    )
    if proactive_msg:
        log_ctx["proactive"] = True
        log_ctx["response"] = proactive_msg
        _persist_log(log_ctx)
        return Reply(text=proactive_msg, experiment_variant=variant.value)

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
    # Feedback loop: if conversation was rated < 3, add extra context
    conv_rating = await _get_conversation_rating(conversation_id)
    top_k = 7 if (conv_rating is not None and conv_rating < 3) else 4
    context_chunks = knowledge.search(user_message, top_k=top_k)
    context_text = knowledge.format_context(context_chunks)
    
    context_summary = await _load_context_summary(conversation_id)
    if context_summary:
        context_text = f"Previous conversation summary:\n{context_summary}\n\n{context_text}"

    tx_ref = _extract_tx_ref(messages)
    history_dicts = _serialize_history(messages[-8:])

    filtered_context, _ = get_page_context_variant(conversation_id, page_context)
    page_prompt = await get_page_prompt_addition(filtered_context)

    # ── NEW: Customer context for personalization ───────────────────
    customer_ctx = await _get_customer_context_summary(customer_phone)
    
    # ── Multi-language support ──────────────────────────────────────
    lang_note = detect_language(user_message)
    
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

    # Multi-language: append language note to system prompt
    if lang_note:
        system_block += f"\n\n{lang_note}"

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

    llm_resp: LLMResponse = await call_llm(plain_messages, max_tokens=500)

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

    # ── Persist the escalation BEFORE returning ────────────────────
    # The fallback text promises "I'll let them know you asked" — so the
    # escalation MUST be written to the DB. Previously this path set
    # escalated=True, wrote a log and a message, and returned WITHOUT
    # calling persist_escalation_sync(). The stats counter incremented,
    # the API response said escalated=true, and the DB got nothing.
    # Customers were told a human had been notified when nobody was.
    try:
        from app.services.charon.escalation_persist import persist_escalation_sync
        persist_escalation_sync(
            conversation_id=conversation_id,
            customer_email=customer_email,
            customer_phone=customer_phone,
            customer_message=user_message,
            history_summary="",
            scenario_id="llm_failure",
            reason=f"LLM error: {llm_resp.error}",
        )
    except Exception as esc_err:
        # The escalation write failed. The customer still gets the fallback
        # message, but we must log loudly so the gap is visible.
        logger.error(
            "ESCALATION PERSIST FAILED — customer was told 'I'll let them know' "
            "but the escalation was NOT saved: %s",
            esc_err,
            extra={**log_ctx, "conversation_id": conversation_id},
        )

    return Reply(text=fallback, escalated=True, error=llm_resp.error, interrupted=True)


def _extract_plan_type(message: str) -> str | None:
    """Extract plan type from message text."""
    msg = message.lower()
    for pt in ("residential", "mobile", "isp", "datacenter"):
        if pt in msg:
            return pt
    if " dc " in msg or msg.startswith("dc ") or msg.endswith(" dc"):
        return "datacenter"
    return None


def _extract_issue(message: str) -> str | None:
    """Extract troubleshooting issue keyword from message text."""
    msg = message.lower()
    issues = {
        "auth_failed": ("auth", "login", "401", "407", "unauthorized", "password"),
        "ip_banned": ("banned", "blocked", "blacklist", "403", "forbidden"),
        "slow_speed": ("slow", "lag", "latency", "timeout", "timed out"),
        "connection_refused": ("refused", "econnrefused", "connection refused"),
        "not_working": ("not working", "doesn't work", "broken", "dead", "down"),
        "expired": ("expired", "expiry", "expiration", "expiring"),
    }
    for issue, keywords in issues.items():
        for kw in keywords:
            if kw in msg:
                return issue
    return None


def _format_tool_result(tool_name: str, data: Any, template: str | None = None) -> str:
    """Format a tool result into a customer-facing reply string."""
    if not isinstance(data, dict):
        return str(data)

    if tool_name == "check_order_status":
        status = data.get("status", "unknown")
        lines = [f"Order status: {status}"]
        if data.get("status_message"):
            lines.append(data["status_message"])
        if data.get("plan_type"):
            lines.append(f"Plan: {data['plan_type']} ({data.get('plan_code', '?')})")
        if data.get("amount_paid_ngn"):
            lines.append(f"Amount paid: ₦{data['amount_paid_ngn']:,.0f}")
        if data.get("delivery_status"):
            lines.append(f"Delivery: {data['delivery_status']}")
        cred = data.get("credential")
        if cred:
            lines.append(
                f"Proxy: {cred.get('proxy_address', '?')}:{cred.get('port', '?')}"
            )
            lines.append(f"Username: {cred.get('username', '?')}")
        return "\n".join(lines)

    if tool_name == "check_proxy_status":
        proxies = data.get("active_proxies", [])
        if not proxies:
            return data.get("message", "No active proxies found.")
        lines = ["Here are your active proxies:"]
        for p in proxies:
            lines.append(
                f"  • {p.get('plan_type', '?')} — "
                f"{p.get('proxy_address', '?')}:{p.get('port', '?')} "
                f"({p.get('protocol', '?')}) — Status: {p.get('status', '?')}"
            )
            if p.get("expires_at"):
                lines.append(f"    Expires: {p['expires_at']}")
            if p.get("data_remaining_gb") is not None:
                lines.append(
                    f"    Data remaining: {p['data_remaining_gb']:.1f}GB / "
                    f"{p.get('data_total_gb', '?')}GB"
                )
        return "\n".join(lines)

    if tool_name == "check_delivery_status":
        status = data.get("delivery_status", "unknown")
        message = data.get("message", "")
        lines = [f"Delivery status: {status}"]
        if message:
            lines.append(message)
        if data.get("emails_sent"):
            lines.append(f"Confirmation emails sent: {data['emails_sent']}")
        return "\n".join(lines)

    if tool_name == "list_customer_orders":
        orders = data.get("orders", [])
        if not orders:
            return data.get("message", "No orders found.")
        lines = ["Here are your orders:"]
        for o in orders:
            lines.append(
                f"  • {o.get('plan_type', '?')} ({o.get('plan_code', '?')}) — "
                f"{o.get('status', '?')} — ₦{o.get('amount', 0):,.0f}"
            )
            if o.get("created_at"):
                lines.append(f"    Ordered: {o['created_at']}")
        return "\n".join(lines)

    if tool_name == "lookup_order":
        status = data.get("status", "unknown")
        lines = [f"Order status: {status}"]
        if data.get("status_message"):
            lines.append(data["status_message"])
        cred = data.get("credential")
        if cred:
            lines.append(
                f"Proxy: {cred.get('proxy_address', '?')}:{cred.get('port', '?')}"
            )
            lines.append(f"Username: {cred.get('username', '?')}")
        return "\n".join(lines)

    if tool_name == "detect_renewal":
        expiring = data.get("expiring_soon", [])
        if not expiring:
            return data.get("message", "No proxies expiring soon.")
        lines = [f"You have {len(expiring)} proxy(s) expiring soon:"]
        for e in expiring:
            lines.append(
                f"  • {e.get('plan_type', '?')} — expires in "
                f"{e.get('days_left', '?')} days"
            )
        lines.append(
            "\nWant me to renew one? Tell me which one and how much data "
            "(min 5 GB for residential/mobile)."
        )
        return "\n".join(lines)

    if tool_name == "check_data_remaining":
        active = data.get("active_data_plans", [])
        if not active:
            return data.get("message", "No active data plans found.")
        total_rem = data.get("total_remaining_gb", 0)
        total_alloc = data.get("total_allocated_gb", 0)
        pct = round(total_rem / total_alloc * 100, 1) if total_alloc > 0 else 0
        return f"Data remaining: {total_rem:.1f}GB / {total_alloc:.1f}GB ({pct}%)"

    if tool_name == "get_product_catalog":
        plans = data.get("plans", [])
        if not plans:
            return "No plans available."
        lines = ["Available plans:"]
        for p in plans[:10]:
            if p.get("price_per_gb"):
                price = f"₦{p['price_per_gb']:,.0f}/GB"
            elif p.get("price_per_ip"):
                price = f"₦{p['price_per_ip']:,.0f}/IP"
            else:
                price = "Contact us"
            lines.append(
                f"  • {p.get('type', '?')} ({p.get('country', '?')}) — {price}"
            )
        return "\n".join(lines)

    if tool_name == "get_setup_guide":
        if isinstance(data, dict) and "setup" in data:
            lines = [data.get("description", "")]
            lines.append("\nSetup steps:")
            for step in data.get("setup", []):
                lines.append(f"  • {step}")
            tips = data.get("tips")
            if tips:
                lines.append("\nTips:")
                for tip in tips:
                    lines.append(f"  • {tip}")
            return "\n".join(lines)
        elif isinstance(data, dict) and "guides" in data:
            lines = [data.get("message", "Here are the available setup guides:")]
            for pt, guide in data.get("guides", {}).items():
                lines.append(f"\n▶ {pt.capitalize()}:")
                lines.append(f"  {guide.get('description', '')}")
                for step in guide.get("setup", []):
                    lines.append(f"  • {step}")
            return "\n".join(lines)
        return str(data)

    if tool_name == "get_troubleshooting":
        if isinstance(data, dict) and "steps" in data:
            symptoms = data.get("symptoms", [])
            header = f"Issue: {symptoms[0]}" if symptoms else "Troubleshooting"
            lines = [header, "\nSteps to fix:"]
            for step in data.get("steps", []):
                lines.append(f"  • {step}")
            return "\n".join(lines)
        return str(data)

    # Default
    if isinstance(data, dict) and "message" in data:
        return data["message"]
    return json.dumps(data, default=str)


async def _run_scenario(
    scenario: scenarios.Scenario,
    messages: list[Message],
    *,
    conversation_id: str | None = None,
    customer_email: str | None = None,
    customer_phone: str | None = None,
    customer_message: str = "",
    history_summary: str = "",
) -> tuple[Any, bool]:
    """Execute a scenario's actions and return (reply_text, escalated).

    Supports three action types:
    - reply: static text (with {{tx_ref_or_unknown}} substitution)
    - escalate: emit an escalation record
    - tool: call a registered tool and format the result
    """
    tx_ref = _extract_tx_ref(messages)
    escalated = False
    reply_text = ""
    tool_results: list[dict] = []

    for action in scenario.actions:
        if action.type == "reply" and action.text:
            if "{{tx_ref_or_unknown}}" in (action.text or ""):
                action.text = action.text.replace(
                    "{{tx_ref_or_unknown}}", tx_ref or "unknown"
                )
            reply_text = action.text or ""
        elif action.type == "escalate":
            escalated = True
            _emit_escalation(
                scenario, action, tx_ref,
                conversation_id=conversation_id,
                customer_email=customer_email,
                customer_phone=customer_phone,
                customer_message=customer_message,
                history_summary=history_summary,
            )
        elif action.type == "tool":
            tool_name = action.tool_name
            if not tool_name or tool_name not in tools.registry.tools:
                logger.warning(
                    "scenario %s: tool %r not registered",
                    scenario.id, tool_name,
                )
                continue

            # Resolve template variables in tool_params
            params = dict(action.tool_params or {})
            plan_type = _extract_plan_type(customer_message)
            issue = _extract_issue(customer_message)
            for key, val in params.items():
                if isinstance(val, str):
                    val = val.replace("{{customer_phone}}", customer_phone or "")
                    val = val.replace("{{tx_ref}}", tx_ref or "")
                    val = val.replace("{{customer_email}}", customer_email or "")
                    val = val.replace("{{plan_type}}", plan_type or "")
                    val = val.replace("{{issue}}", issue or "")
                    params[key] = val

            # Call the tool
            result = await tools.registry.call(tool_name, **params)
            tool_results.append({
                "tool": tool_name,
                "params": params,
                "result": result.to_dict(),
            })

            if result.ok:
                formatted = _format_tool_result(
                    tool_name, result.data, action.response_template
                )
                if formatted:
                    reply_text = formatted
            else:
                logger.warning(
                    "scenario %s: tool %s failed: %s",
                    scenario.id, tool_name, result.error,
                )
                reply_text = (
                    f"I couldn't complete that automatically. "
                    f"{result.error or 'Unknown error'}. "
                    f"Let me connect you with the team at styxproxy.com/contact."
                )

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
        llm_resp = await call_llm(tool_prompt_messages, max_tokens=400)
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
            if tool_name in ("lookup_order", "lookup_payment_status", "generate_order_link", "generate_receipt_link", "get_customer_context", "list_customer_orders", "check_data_remaining", "get_referral_info", "detect_renewal", "escalate_bulk_inquiry", "initiate_renewal", "check_order_status", "check_proxy_status", "check_delivery_status", "lookup_order_by_email"):
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
            follow_up = await call_llm(follow_up_messages, max_tokens=400)
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
        follow_up = await call_llm(follow_up_messages, max_tokens=400)
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
    # Handle longcat_tool_call format: toolname\nparams
    for match in _LONGCAT_TOOL_CALL.finditer(text):
        tool_name = match.group(1).strip()
        params_raw = match.group(3).strip()
        params = {}
        if params_raw:
            try:
                import json as _json
                params = _json.loads(params_raw)
            except Exception:
                pass
        return {'tool': tool_name, 'params': params}
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
    """Append one conversation record to the JSONL log.

    `ctx` carries `user_message`, and this file is served back verbatim by the
    unauthenticated `GET /charon/logs` and `GET /charon/conversations`. So the
    value is screened HERE, at the write, rather than relying on every future
    caller having passed through the router's ingress guard first. This is the
    second of the two gates; `_read_logs` screens on the way out as well, which
    is what protects the records already on disk.
    """
    safe = redact_mapping(ctx)
    log_dir = os.getenv("CHARON_LOG_DIR", "/tmp")
    log_path = os.path.join(log_dir, "charon.log")
    try:
        os.makedirs(log_dir, exist_ok=True)
        with open(log_path, "a") as fh:
            fh.write(json.dumps({"ts": datetime.now(timezone.utc).isoformat(), **safe}) + "\n")
    except OSError:
        pass
    logger.info("charon.reply", extra={"charon": safe})


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


# ─── Proactive Outreach ─────────────────────────────────────────────────────

async def check_proactive_triggers(
    conversation_id: str,
    page_context: dict,
    customer_email: str | None = None,
    customer_phone: str | None = None,
    customer_name: str | None = None,
) -> str | None:
    """Check proactive outreach triggers based on page context and customer state.

    Returns a proactive message string if a trigger fires, None otherwise.
    """
    if not page_context:
        return None

    page_url = page_context.get("page_url", "") or page_context.get("url", "")
    page_type = page_context.get("page_type", "")
    time_on_page = page_context.get("time_on_page_seconds", 0) or page_context.get("duration_seconds", 0)
    event_type = page_context.get("event_type", "") or page_context.get("trigger", "")

    # Trigger a) checkout page >30s
    if ("checkout" in page_url or "cart" in page_url or page_type == "checkout") and time_on_page > 30:
        return "Need help choosing? I can compare plans for you."

    # Trigger b) plan detail page
    if page_type == "plan_detail" or ("plan" in page_url and ("detail" in page_url or "view" in page_url)):
        return "Want me to explain how this plan works?"

    # Trigger c) payment just completed
    if event_type == "payment_completed" or page_context.get("payment_completed"):
        return "Your order is confirmed! Want setup instructions?"
    if "payment" in page_url and "success" in page_url:
        return "Your order is confirmed! Want setup instructions?"

    # Trigger d) proxy expiring <7 days — use detect_renewal tool
    if customer_phone:
        try:
            renew_result = await tools.registry.call("detect_renewal", customer_phone=customer_phone)
            if renew_result.ok and renew_result.data.get("expiring_soon"):
                n = len(renew_result.data["expiring_soon"])
                if n == 1:
                    expiring = renew_result.data["expiring_soon"][0]
                    return f"Your {expiring.get('plan_type', 'proxy')} proxy expires in {expiring.get('days_left', '?')} days. Want me to renew it now?"
                else:
                    return f"You have {n} proxies expiring soon. Want me to renew them now?"
        except Exception:
            pass

    return None


# ─── Conversation Rating (Feedback Loop) ───────────────────────────────────

async def _get_conversation_rating(conversation_id: str) -> int | None:
    """Get the rating for a conversation (1-5 stars). Returns None if unrated."""
    try:
        from app.database import async_session
        from app.models import CharonConversation
        from sqlalchemy import select

        async with async_session() as session:
            stmt = select(CharonConversation.rating).where(
                CharonConversation.session_id == conversation_id
            )
            result = await session.execute(stmt)
            rating = result.scalar_one_or_none()
            return rating if rating is not None else None
    except Exception as exc:
        logger.warning("Failed to get conversation rating: %s", exc)
        return None


# ─── Multi-language Detection ──────────────────────────────────────────────

_LANG_RANGES = [
    ("Chinese", r"[\u4e00-\u9fff]"),
    ("Japanese", r"[\u3040-\u309f\u30a0-\u30ff]"),
    ("Korean", r"[\uac00-\ud7af]"),
    ("Arabic", r"[\u0600-\u06ff]"),
    ("Russian", r"[\u0400-\u04ff]"),
    ("Hindi", r"[\u0900-\u097f]"),
    ("Thai", r"[\u0e00-\u0e7f]"),
    ("Greek", r"[\u0370-\u03ff]"),
    ("Hebrew", r"[\u0590-\u05ff]"),
]

_LANG_WORDS = {
    "Spanish": {"el", "la", "los", "las", "un", "una", "que", "por", "con", "para", "es", "está", "como", "pero", "más", "este", "esta", "no", "sí", "también", "ya", "cuando", "donde", "porque", "quien", "cual", "estoy", "soy", "eres", "somos", "son", "fui", "fue", "ser", "estar", "haber", "tener", "hacer", "poder", "decir", "ir", "ver", "dar", "saber", "querer", "llegar", "pasar", "deber", "poner", "parecer", "quedar", "creer", "hablar", "llevar", "dejar", "seguir", "encontrar", "llamar", "venir", "pensar", "salir", "volver", "tomar", "conocer", "vivir", "sentir", "tratar", "mirar", "contar", "empezar", "esperar", "buscar", "existir", "entrar", "trabajar", "escribir", "perder", "entender", "pedir", "recibir", "recordar", "terminar", "permitir", "aparecer", "conseguir", "comenzar", "servir", "sacar", "necesitar", "mantener", "resultar", "leer", "caer", "cambiar", "presentar", "crear", "abrir", "considerar", "oír", "acabar", "convertir", "ganar", "formar", "traer", "partir", "morir", "aceptar", "realizar", "suponer", "comprender", "lograr", "explicar", "preguntar", "tocar", "reconocer", "estudiar", "alcanzar", "nacer", "dirigir", "correr", "utilizar", "pagar", "ayudar", "jugar", "escuchar", "cumplir", "ofrecer", "descubrir", "levantar", "intentar", "usar"},
    "French": {"le", "la", "les", "un", "une", "des", "et", "est", "sont", "je", "tu", "il", "elle", "nous", "vous", "ils", "elles", "me", "te", "se", "leur", "ne", "pas", "plus", "si", "en", "qui", "que", "quoi", "dont", "où", "quand", "comment", "pourquoi", "combien", "quel", "quelle", "ce", "cet", "cette", "ces", "avoir", "être", "faire", "dire", "aller", "voir", "savoir", "pouvoir", "falloir", "vouloir", "venir", "devoir", "prendre", "trouver", "donner", "parler", "aimer", "passer", "demander", "tenir", "sembler", "laisser", "rester", "penser", "entendre", "regarder", "répondre", "rendre", "attendre", "sortir", "vivre", "reprendre", "connaître", "croire", "sentir", "atteindre", "revenir", "comprendre", "mettre", "porter", "devenir", "appeler", "partir", "décider", "arriver", "servir", "paraître", "reposer", "retourner", "sembler"},
    "German": {"der", "die", "das", "ein", "eine", "und", "ist", "sind", "ich", "du", "er", "sie", "es", "wir", "ihr", "mich", "dich", "ihn", "uns", "euch", "mein", "dein", "sein", "ihr", "unser", "euer", "nicht", "kein", "keine", "auch", "nur", "schon", "noch", "sehr", "hier", "dort", "wo", "was", "wer", "wann", "warum", "wie", "welch", "welche", "dieser", "diese", "dieses", "haben", "sein", "werden", "können", "müssen", "wollen", "sollen", "dürfen", "lassen", "machen", "geben", "kommen", "sagen", "wissen", "sehen", "stehen", "finden", "bleiben", "liegen", "denken", "nehmen", "halten", "bringen", "leben", "fahren", "legen", "zeigen", "führen", "sprechen", "spielen", "laufen", "tragen", "stellen", "beginnen", "kennen", "gelten"},
    "Portuguese": {"o", "a", "os", "as", "um", "uma", "e", "é", "são", "eu", "tu", "ele", "ela", "nós", "vós", "eles", "elas", "me", "te", "se", "não", "sim", "também", "já", "ainda", "mais", "menos", "muito", "pouco", "bem", "mal", "aqui", "ali", "onde", "quando", "como", "porque", "quanto", "quem", "qual", "quais", "este", "esta", "esse", "essa", "ser", "estar", "ter", "haver", "fazer", "poder", "dizer", "ir", "ver", "dar", "saber", "querer", "chegar", "passar", "dever", "pôr", "parecer", "ficar", "crer", "falar", "levar", "deixar", "seguir", "encontrar", "chamar", "vir", "pensar", "sair", "voltar", "tomar", "conhecer", "viver", "sentir", "tratar", "olhar", "contar", "começar", "esperar", "buscar", "existir", "entrar", "trabalhar", "escrever", "perder", "entender", "pedir", "receber", "lembrar", "terminar", "permitir", "aparecer", "conseguir", "servir", "sacar", "necessitar", "manter", "resultar", "ler", "cair", "mudar", "apresentar", "criar", "abrir", "considerar", "ouvir", "acabar", "converter", "ganhar", "formar", "trazer", "partir", "morrer", "aceitar", "realizar", "supor", "compreender", "lograr", "explicar", "perguntar", "tocar", "reconhecer", "estudar", "alcançar", "nascer", "dirigir", "correr", "utilizar", "pagar", "ajudar", "jogar", "escutar", "cumprir", "ofrecer", "descobrir", "levantar", "tentar", "usar"},
    "Italian": {"il", "lo", "la", "i", "gli", "le", "un", "uno", "una", "e", "è", "sono", "io", "tu", "lui", "lei", "noi", "voi", "loro", "mi", "ti", "si", "ci", "vi", "mio", "tuo", "suo", "nostro", "vostro", "non", "sì", "anche", "già", "ancora", "più", "meno", "molto", "poco", "bene", "male", "qui", "lì", "dove", "quando", "come", "perché", "quanto", "chi", "quale", "quali", "questo", "questa", "quello", "quella", "essere", "avere", "fare", "dire", "andare", "vedere", "sapere", "potere", "volere", "dovere", "venire", "prendere", "trovare", "dare", "parlare", "amare", "passare", "chiedere", "tenere", "sembrare", "lasciare", "restare", "pensare", "sentire", "guardare", "rispondere", "rendere", "attendere", "uscire", "vivere", "riprendere", "conoscere", "credere", "arrivare", "servire", "apparire", "riposare", "tornare", "cominciare", "permettere", "spiegare", "chiamare", "partire", "decidere", "riuscire", "finire", "mancare", "leggere", "cadere", "cambiare", "presentare", "creare", "aprire", "considerare", "compiere", "convertire", "vincere", "formare", "portare", "morire", "accettare", "realizzare", "supporre", "comprendere", "raggiungere", "toccare", "riconoscere", "studiare", "nascere", "dirigere", "correre", "utilizzare", "pagare", "aiutare", "giocare", "ascoltare", "offrire", "scoprire", "provare", "usare"},
}


def detect_language(text: str) -> str | None:
    """Detect if text is non-English using heuristics.

    Returns a language note string for the system prompt if non-English
    detected, or None if the text appears to be English.
    """
    if not text or len(text.strip()) < 3:
        return None

    text_lower = text.lower()
    words = set(re.findall(r"[a-zà-ÿ]+", text_lower))

    # Check character-range heuristics first (CJK, Arabic, Cyrillic, etc.)
    for lang_name, pattern in _LANG_RANGES:
        if re.search(pattern, text):
            return _lang_note(lang_name)

    # Check word-count heuristics for European languages
    lang_scores: dict[str, int] = {}
    for lang_name, lang_words in _LANG_WORDS.items():
        overlap = len(words & lang_words)
        if overlap >= 3:
            lang_scores[lang_name] = overlap

    if lang_scores:
        best_lang = max(lang_scores, key=lambda k: lang_scores[k])
        if lang_scores[best_lang] >= 3:
            return _lang_note(best_lang)

    return None


def _lang_note(language: str) -> str:
    """Generate a system-prompt note for the detected language."""
    return (
        f"User is writing in {language}. "
        f"Respond in the same language if possible."
    )
