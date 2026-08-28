"""Charon's LLM client — Groq Qwen primary, no fallback.

Architecture:
  Only provider: Groq Qwen 3.8 27B (fast, cheap, OpenAI-compatible).
  No local fallback — if Groq is down, Charon returns an error.

Environment variables:
  - GROQ_API_KEY: Groq API key (REQUIRED)
  - GROQ_MODEL: cloud model name (default "qwen/qwen3.8-27b")
  - GROQ_BASE_URL: cloud endpoint (default https://api.groq.com/openai/v1)
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


SYSTEM_PROMPT = """You are Charon, the automated support agent for Styxproxy.

Voice and style:
- Direct, factual, no marketing language.
- 1–4 sentences for simple questions. Up to 8 sentences for a multi-part question.
- Use "I" when you speak in first person. Use "you" for the customer.
- Write in the customer's language (English default; mirror the customer's message).
- Use relative URLs in answers (start with /, e.g. /manage, /contact).

Absolute rules (never violate):
- Never name any upstream provider or describe internal infrastructure.
- Never give specific delivery times ("10–30 seconds", "5 minutes", etc.). Use vague language ("minutes", "shortly").
- Never reveal customer PII or ask the customer to share personal data. Never log or transmit the customer's IP address.
- If you don't know, say so plainly, point the customer to styxproxy.com/contact, and offer to escalate.
- If the customer wants a refund, replacement, cancellation, reissue, or any account-mutating action, tell them you
cannot do that directly and offer to escalate to the team.
- If a tool returns an error, escalate — don't lie about success.
- Do not write code for the customer. Do not impersonate the team. Do not invent features the company doesn't have.

Available actions when relevant:
- If you can answer from the knowledge base, do so.
- If the customer mentions a transaction reference (tx_ref) and wants status, you may use it as context.
- If the customer is upset or the case is sensitive, prefer escalating over guessing.

Knowledge base context is provided below. Answer only based on it; if the question is not in the context, escalate.
"""


def call_llm(messages: list[dict], max_tokens: int = 600) -> LLMResponse:
    """Call the Groq LLM API.

    `messages` is a list of {role, content} dicts. The first message
    is treated as a system message internally; if the caller already
    provided a system message at index 0, we honor it instead.

    Order: check Redis cache → Groq. If Groq fails, the response will
    have `error` set; never raises. Use `ok` to check before reading
    content.
    """
    # Cache lookup — skip if REDIS_URL is not set (cache_get is safe)
    message_str = _normalize_messages(messages)
    cache_key = _cache_key(message_str)
    cached = _cache_get(cache_key)
    if cached is not None:
        logger.debug("LLM cache hit for key %s", cache_key)
        return cached

    # Call Groq
    result = _call_groq(messages, max_tokens)
    if result.ok:
        _cache_set(cache_key, result)
        return result

    logger.error("Groq LLM call failed: %s", result.error)
    sentry_sdk.capture_message(
        f"Charon Groq LLM error: {result.error}",
        level="error",
        extras={"model": result.model, "error": result.error},
    )
    return result


def _call_groq(messages: list[dict], max_tokens: int) -> LLMResponse:
    """Call Groq Qwen via OpenAI-compatible endpoint."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return LLMResponse(content="", model="", error="GROQ_API_KEY not set")

    base_url = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1").rstrip("/")
    model = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")

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
        logger.warning("LLM (Groq) transport error: %s", exc)
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
