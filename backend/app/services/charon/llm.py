"""Charon's LLM client.

Calls the local MiniCPM5 1B model via the LiteLLM proxy sidecar
(OpenAI-compatible chat endpoint at /v1/chat/completions). Cloud
MiniMax-M2 fallback is available by setting CHARON_LLM_PROVIDER=cloud.

Environment variables:
  - LITELLM_BASE_URL: where the LiteLLM proxy listens (default
    http://127.0.0.1:4000 — same network as the api container)
  - LITELLM_API_KEY: master key the proxy expects
  - MINICPM_MODEL: model name to send for local calls (default "minicpm5")
  - MINIMAX_MODEL: model name to send for cloud calls (default "cloud-minimax-m2")
  - CHARON_LLM_PROVIDER: "local" (default) or "cloud"

The interface here is stable; swapping model providers is a config
change (edit compose env), not a code change. MiniCPM5 1B is on the VPS
(84.247.132.12, Ollama on host port 11434). LiteLLM sits in front of it
for unified logging and routing.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass

import httpx
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

    Routes to:
      - Local MiniCPM5 via Ollama when CHARON_LLM_PROVIDER is unset / "local"
      - Cloud MiniMax-M2 when CHARON_LLM_PROVIDER=cloud

    On any failure, returns LLMResponse with `error` set; never raises.
    Use `ok` to check before reading content.
    """
    provider = os.getenv("CHARON_LLM_PROVIDER", "local").strip().lower()

    if provider == "cloud":
        return _call_cloud(messages, max_tokens)
    return _call_local(messages, max_tokens)


def _call_local(messages: list[dict], max_tokens: int) -> LLMResponse:
    """Call MiniCPM5 via the LiteLLM proxy (sidecar).

    All provider abstraction lives in the proxy; this client only knows
    how to speak OpenAI-compatible chat-completions. The LiteLLM proxy
    itself decides whether to route to local Ollama, cloud MiniMax-M2, or
    another provider based on the requested `model` name.
    """
    base_url = os.getenv("LITELLM_BASE_URL", "http://127.0.0.1:4000").rstrip("/")
    api_key = os.getenv("LITELLM_API_KEY", "sk-styxproxy-local-dev-only")
    model = os.getenv("MINICPM_MODEL", "minicpm5")

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
        "stream": False,
    }

    try:
        # Local CPU inference is slow; 120s read is generous.
        resp = httpx.post(
            f"{base_url}/v1/chat/completions",
            json=payload,
            headers=headers,
            timeout=httpx.Timeout(connect=5.0, read=120.0, write=10.0, pool=5.0),
        )
    except httpx.HTTPError as exc:
        logger.warning("LLM (local via LiteLLM) transport error: %s", exc)
        return LLMResponse(content="", model=model, error=f"transport error: {exc}")

    return _parse_openai_compatible_response(resp, model)


def _call_cloud(messages: list[dict], max_tokens: int) -> LLMResponse:
    """Call MiniMax-M2 via OpenRouter-compatible endpoint."""
    api_key = os.getenv("MINIMAX_API_KEY")
    if not api_key:
        return LLMResponse(content="", model="", error="MINIMAX_API_KEY not set (cloud provider)")

    base_url = os.getenv("MINIMAX_BASE_URL", "https://api.minimax.chat/v1").rstrip("/")
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
            timeout=httpx.Timeout(connect=5.0, read=30.0, write=10.0, pool=5.0),
        )
    except httpx.HTTPError as exc:
        logger.warning("LLM (cloud) transport error: %s", exc)
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
