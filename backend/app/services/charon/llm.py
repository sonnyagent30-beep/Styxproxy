"""Charon's LLM client.

Calls MiniMax-M2 chat completions (OpenAI-compatible endpoint).
The interface here is stable; if/when we wire this through n8n, the
function signature stays the same and only the body changes.

Environment variables:
  - MINIMAX_API_KEY: required (raises on missing)
  - MINIMAX_BASE_URL: optional override; defaults to OpenRouter-compatible
    MiniMax endpoint
  - MINIMAX_MODEL: optional model name; defaults to "minimax/minimax-m2"

These are intentionally generically-named; the model provider can be
swapped without code changes (set the env vars to point at any
OpenAI-compatible endpoint).
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass

import httpx

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
- If the customer wants a refund, replacement, cancellation, reissue, or any account-mutating action, tell them you cannot do that directly and offer to escalate to the team.
- If a tool returns an error, escalate — don't lie about success.
- Do not write code for the customer. Do not impersonate the team. Do not invent features the company doesn't have.

Available actions when relevant:
- If you can answer from the knowledge base, do so.
- If the customer mentions a transaction reference (tx_ref) and wants status, you may use it as context.
- If the customer is upset or the case is sensitive, prefer escalating over guessing.

Knowledge base context is provided below. Answer only based on it; if the question is not in the context, escalate.
"""


def call_llm(messages: list[dict], max_tokens: int = 600) -> LLMResponse:
    """Call the LLM API.

    `messages` is a list of {role, content} dicts. The first message
    is treated as a system message internally; if the caller already
    provided a system message at index 0, we honor it instead.

    On any failure, returns LLMResponse with `error` set; never raises.
    Use `ok` to check before reading content.
    """
    api_key = os.getenv("MINIMAX_API_KEY")
    if not api_key:
        return LLMResponse(content="", model="", error="MINIMAX_API_KEY not set in environment")

    base_url = os.getenv("MINIMAX_BASE_URL", "https://api.MiniMax.chat/v1")
    model = os.getenv("MINIMAX_MODEL", "minimax/MiniMax-M2")

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
            timeout=30.0,
        )
    except httpx.HTTPError as exc:
        logger.warning("LLM request transport error: %s", exc)
        return LLMResponse(content="", model=model, error=f"transport error: {exc}")

    if resp.status_code >= 400:
        logger.warning("LLM API error %d: %s", resp.status_code, resp.text[:300])
        return LLMResponse(
            content="", model=model,
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
