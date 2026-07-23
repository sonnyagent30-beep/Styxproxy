"""Observability: Sentry + Redis cache.

Sentry: capture all uncaught exceptions + custom events. Activated only
when SENTRY_DSN is set in the environment (no-op otherwise).

Redis: simple async cache with TTL. Falls back to in-process dict when
Redis is unavailable. Used by blog router to cache list responses.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ─── Sentry ────────────────────────────────────────────────────────────────

_SENTRY_DSN = os.environ.get("SENTRY_DSN", "").strip()
_SENTRY_TRACES_SAMPLE_RATE = float(os.environ.get("SENTRY_TRACES_SAMPLE_RATE", "0.1"))


def init_sentry() -> None:
    """Initialize Sentry if DSN is configured.

    Safe to call multiple times (idempotent).
    No-op when DSN is not set.
    """
    if not _SENTRY_DSN:
        logger.info("Sentry DSN not set — observability disabled")
        return

    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration

        sentry_sdk.init(
            dsn=_SENTRY_DSN,
            traces_sample_rate=_SENTRY_TRACES_SAMPLE_RATE,
            environment=os.environ.get("ENVIRONMENT", "production"),
            release=os.environ.get("RELEASE", "styxproxy-backend@1.0.0"),
            integrations=[
                FastApiIntegration(),
                StarletteIntegration(),
                LoggingIntegration(level=logging.INFO, event_level=logging.ERROR),
            ],
        )
        logger.info("Sentry initialized", extra={"dsn_set": bool(_SENTRY_DSN)})
    except Exception as exc:
        # Don't crash the app on observability init failure
        logger.exception("Sentry init failed: %s", exc)


# ─── Redis cache ───────────────────────────────────────────────────────────

_redis_client: Any = None
_inproc_cache: dict[str, tuple[float, Any]] = {}  # key -> (expires_at, value)


async def get_redis() -> Any:
    """Return a Redis async client. None if Redis is not configured.

    Falls back gracefully: any connection error returns None so the
    caller can decide to skip the cache.
    """
    global _redis_client
    if _redis_client is not None:
        return _redis_client

    url = os.environ.get("REDIS_URL", "").strip()
    if not url:
        return None

    try:
        import redis.asyncio as redis_async
        _redis_client = redis_async.from_url(url, decode_responses=True)
        # quick ping to fail fast if Redis is down
        await _redis_client.ping()
        return _redis_client
    except Exception as exc:
        logger.warning("Redis unavailable, falling back to in-process cache: %s", exc)
        _redis_client = None
        return None


async def cache_get(key: str) -> Optional[Any]:
    """Get a value from cache. Returns None on miss or any error."""
    try:
        client = await get_redis()
        if client is not None:
            raw = await client.get(key)
            if raw is not None:
                return json.loads(raw)
            return None
    except Exception as exc:
        logger.debug("cache_get redis error: %s", exc)

    # In-process fallback
    import time
    entry = _inproc_cache.get(key)
    if entry is None:
        return None
    expires_at, value = entry
    if expires_at < time.time():
        _inproc_cache.pop(key, None)
        return None
    return value


async def cache_set(key: str, value: Any, ttl_seconds: int = 60) -> None:
    """Store a value in cache. Best-effort; errors are logged but not raised."""
    try:
        client = await get_redis()
        if client is not None:
            await client.set(key, json.dumps(value, default=str), ex=ttl_seconds)
            return
    except Exception as exc:
        logger.debug("cache_set redis error: %s", exc)

    # In-process fallback
    import time
    _inproc_cache[key] = (time.time() + ttl_seconds, value)
    # simple LRU-style cap
    if len(_inproc_cache) > 1000:
        _inproc_cache.pop(next(iter(_inproc_cache)), None)


async def cache_delete(key: str) -> None:
    """Invalidate a key."""
    try:
        client = await get_redis()
        if client is not None:
            await client.delete(key)
    except Exception:
        pass
    _inproc_cache.pop(key, None)


async def cache_delete_prefix(prefix: str) -> None:
    """Invalidate all keys with a given prefix (best-effort)."""
    try:
        client = await get_redis()
        if client is not None:
            cursor = 0
            while True:
                cursor, keys = await client.scan(cursor=cursor, match=f"{prefix}*", count=100)
                if keys:
                    await client.delete(*keys)
                if cursor == 0:
                    break
    except Exception:
        pass
    # In-process: filter by prefix
    for k in list(_inproc_cache.keys()):
        if k.startswith(prefix):
            _inproc_cache.pop(k, None)
