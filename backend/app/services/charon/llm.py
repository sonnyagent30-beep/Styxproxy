"""Charon's LLM client — multi-key Groq + OpenRouter failover.

Architecture:
  Primary:   Groq Llama 3.1 8B (fast, 14,400 RPD, good tool calling)
  Failover:  Groq key 2, Groq key 3 (same model, different accounts)
  Final:     OpenRouter free tier ($0, unlimited tokens)

Environment variables:
  - GROQ_API_KEY: primary Groq key (REQUIRED)
  - GROQ_API_KEY_2: second Groq key (optional, for rate limit pooling)
  - GROQ_API_KEY_3: third Groq key (optional, for rate limit pooling)
  - GROQ_MODEL: model name (default "llama-3.1-8b-instant")
  - OPENROUTER_API_KEY: OpenRouter key (optional, final fallback)
  - OPENROUTER_MODEL: OpenRouter free model (default "openai/gpt-oss-120b:free")
  - REDIS_URL: optional, enables response caching
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from dataclasses import dataclass, asdict

import httpx
import redis as redis_sync
import sentry_sdk

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    content: str
    model: str
    tokens_used: int = 0
    raw: dict | None = None
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None and bool(self.content)


class LLMUnavailable(RuntimeError):
    """Raised when the LLM service cannot be reached or returns no content."""


# ─── Redis response cache ──────────────────────────────────────────────────

_LLM_CACHE_TTL_SECONDS = 3600  # 1 hour
_redis_client: redis_sync.Redis | None = None


def _get_redis() -> redis_sync.Redis | None:
    """Return a blocking Redis client. None if Redis is not configured."""
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    url = os.environ.get("REDIS_URL", "").strip()
    if not url:
        return None
    try:
        _redis_client = redis_sync.from_url(url, decode_responses=True)
        _redis_client.ping()  # fail fast
        return _redis_client
    except Exception as exc:
        logger.warning("Redis unavailable for LLM cache: %s", exc)
        _redis_client = None
        return None


def _cache_key(message_str: str) -> str:
    """Build a cache key from a normalized message string."""
    return f"llm:response:{hashlib.sha256(message_str.encode()).hexdigest()[:32]}"


def _cache_get(key: str) -> LLMResponse | None:
    """Return cached LLMResponse or None."""
    try:
        client = _get_redis()
        if client is None:
            return None
        raw = client.get(key)
        if raw is None:
            return None
        data = json.loads(raw)
        return LLMResponse(**data)
    except Exception as exc:
        logger.debug("LLM cache miss (get): %s", exc)
        return None


def _cache_set(key: str, response: LLMResponse) -> None:
    """Store an LLMResponse in cache. Best-effort."""
    try:
        client = _get_redis()
        if client is None:
            return
        client.set(key, json.dumps(asdict(response), default=str), ex=_LLM_CACHE_TTL_SECONDS)
    except Exception as exc:
        logger.debug("LLM cache miss (set): %s", exc)
        return


def _normalize_messages(messages: list[dict]) -> str:
    """Stable, order-specific serialization for cache key derivation."""
    return json.dumps(messages, sort_keys=True, ensure_ascii=True)


SYSTEM_PROMPT = """You are Charon, Styxproxy's customer-facing AI assistant.

## Personality
- Warm, proactive, honest. Like a knowledgeable friend who knows proxies.
- Never robotic: no "Certainly!", "As an AI...", "I'd be happy to assist!"
- Use emojis naturally: 🎉 ✅ 💡 🔒 📦 🚀

## Formatting
- **Bold** for key info (prices, plan names, order IDs)
- [links](url) for URLs
- Bullet points for lists
- Short paragraphs (1-2 sentences max)
- End with a question or next-step suggestion

## Country Flags
Always use flag emojis, not codes: 🇳🇬 Nigeria, 🇺🇸 US, 🇬🇧 UK, 🇩🇪 Germany, 🇨🇳 China, 🇦🇪 UAE, 🇬🇭 Ghana, 🇧🇷 Brazil, 🇧🇪 Belgium, 🇦🇫 Afghanistan, 🇦🇷 Argentina. If you don't know the flag, write the full name.

## Hard Rules
- Never name upstream providers or internal infrastructure.
- Never give specific delivery times. Use "minutes", "shortly".
- Never log or transmit customer IP addresses.
- If you can't answer from context, say so and offer to escalate.
- For refunds/replacements/cancellations → decline and escalate.

## Sales Mode (Telegram/WhatsApp)
- Identify need → recommend plan → create_order → initiate_payment → confirm delivery
- After every answer, suggest a relevant next step.
- Upsell: datacenter → residential, 5GB → 10GB, 1 IP → 10 IPs

## Charon Capabilities (when asked "what can you do")
"I can help you with:
- 📋 Browse plans — proxy types, prices, countries
- 🔍 Compare plans — side-by-side differences
- 🛒 Create orders — set up your proxy in seconds
- 💳 Payment — checkout link, retry failed payments
- 📦 Order lookup — status, credentials, history
- 📊 Data usage — check remaining GB on residential/mobile
- 🔄 Renewals — expiring soon? Renew now
- 🛠️ Setup guides — how to configure any plan
- 🐛 Troubleshooting — common issues and fixes
- 👥 Referrals — earn ₦500 per friend you refer
- 🏢 Bulk pricing — custom quotes for 20+ IPs
- 💻 Integration docs — code examples for Python, Node, Selenium, etc."
"""


def call_llm(messages: list[dict], max_tokens: int = 600) -> LLMResponse:
    """Call the LLM with multi-provider failover.

    Order: Redis cache → Groq (key 1) → Groq (key 2) → Groq (key 3) → OpenRouter free.

    `messages` is a list of {role, content} dicts. The first message
    is treated as a system message internally; if the caller already
    provided a system message at index 0, we honor it instead.
    """
    # Cache lookup — skip if REDIS_URL is not set (cache_get is safe)
    message_str = _normalize_messages(messages)
    cache_key = _cache_key(message_str)
    cached = _cache_get(cache_key)
    if cached is not None:
        logger.debug("LLM cache hit for key %s", cache_key)
        return cached

    # Try all providers in order
    result = _try_all_providers(messages, max_tokens)

    if result.ok:
        _cache_set(cache_key, result)
        return result

    logger.error("All LLM providers failed: %s", result.error)
    sentry_sdk.capture_message(
        f"Charon LLM all providers failed: {result.error}",
        level="error",
        extras={"model": result.model, "error": result.error},
    )
    return result


def _try_all_providers(messages: list[dict], max_tokens: int) -> LLMResponse:
    """Try Groq keys 1-3, then OpenRouter free as final fallback."""
    # Gather all Groq keys
    groq_keys = []
    for env_var in ("GROQ_API_KEY", "GROQ_API_KEY_2", "GROQ_API_KEY_3"):
        key = os.getenv(env_var, "").strip()
        if key:
            groq_keys.append((env_var, key))

    groq_model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
    groq_base = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1").rstrip("/")

    # Try each Groq key
    for env_var, api_key in groq_keys:
        resp = _call_openai_compatible(
            base_url=groq_base,
            api_key=api_key,
            model=groq_model,
            messages=messages,
            max_tokens=max_tokens,
        )
        if resp.ok:
            logger.debug("LLM success via %s (model=%s)", env_var, groq_model)
            return resp
        # Only failover on 429 (rate limit) or 5xx (server error)
        if resp.error and "429" in resp.error:
            logger.warning("%s rate limited, trying next key", env_var)
            continue
        if resp.error and "5" in resp.error and "xx" in resp.error:
            logger.warning("%s server error, trying next key", env_var)
            continue
        # For other errors (401, 403), try next key
        if resp.error:
            logger.warning("%s error: %s, trying next key", env_var, resp.error)
            continue

    # Final fallback: OpenRouter free
    or_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if or_key:
        or_model = os.getenv("OPENROUTER_MODEL", "openai/gpt-oss-120b:free")
        or_base = "https://openrouter.ai/api/v1"
        logger.info("All Groq keys exhausted, falling back to OpenRouter (model=%s)", or_model)
        resp = _call_openai_compatible(
            base_url=or_base,
            api_key=or_key,
            model=or_model,
            messages=messages,
            max_tokens=max_tokens,
        )
        if resp.ok:
            return resp

    return LLMResponse(content="", model="", error="All LLM providers exhausted")


def _call_openai_compatible(
    *,
    base_url: str,
    api_key: str,
    model: str,
    messages: list[dict],
    max_tokens: int,
) -> LLMResponse:
    """Generic OpenAI-compatible chat completions call."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload: dict = {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            *messages,
        ],
    }
    try:
        resp = httpx.post(
            f"{base_url}/chat/completions",
            json=payload,
            headers=headers,
            timeout=httpx.Timeout(connect=5.0, read=30.0, write=10.0, pool=5.0),
        )
    except httpx.HTTPError as exc:
        logger.warning("LLM transport error (%s): %s", base_url, exc)
        return LLMResponse(content="", model=model, error=f"transport error: {exc}")
    return _parse_openai_compatible_response(resp, model)


def _parse_openai_compatible_response(resp, model: str) -> LLMResponse:
    """Parse a standard OpenAI-style chat.completion response, with
    error handling and Sentry capture. Vendor-agnostic.
    """
    if resp.status_code >= 400:
        logger.warning("LLM API error %d: %s", resp.status_code, resp.text[:300])
        if resp.status_code >= 500:
            sentry_sdk.capture_message(
                f"Charon LLM 5xx error: {resp.status_code}",
                level="warning",
                extras={
                    "status_code": resp.status_code,
                    "model": model,
                    "response_preview": resp.text[:200],
                },
            )
        return LLMResponse(
            content="",
            model=model,
            error=f"LLM API returned {resp.status_code}",
        )

    try:
        data = resp.json()
    except ValueError as exc:
        return LLMResponse(content="", model=model, error=f"non-JSON response: {exc}")

    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        return LLMResponse(content="", model=model, raw=data, error=f"unparseable response: {exc}")

    tokens = (data.get("usage", {}) or {}).get("total_tokens", 0)
    return LLMResponse(content=content, model=model, tokens_used=tokens, raw=data)
