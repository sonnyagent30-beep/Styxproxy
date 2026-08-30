"""Rate limiter instance — imported by routers, not main (avoids circular import).

Two limiters:
  1. `limiter` — IP-based, for general API protection (default routes)
  2. `customer_limiter` — per-customer, for Charon chat endpoints

Both use Redis for cross-worker sharing (moving-window strategy).
Without Redis, in-memory storage makes the limit per-process
(N workers → effective limit = N × declared limit).
"""

import json
import logging
from typing import Optional

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import get_settings

logger = logging.getLogger(__name__)

_settings = get_settings()

# ─── IP-based limiter (general API protection) ──────────────────────────────

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[f"{_settings.rate_limit_per_minute}/minute"],
    # Shared across all workers when running with --workers > 1.
    storage_uri=_settings.redis_url,
    # Use the "moving-window" strategy so the window slides continuously
    # rather than resetting on a fixed boundary.
    strategy="moving-window",
)


# ─── Per-customer limiter (Charon chat) ─────────────────────────────────────

_redis_client = None


def _get_redis():
    """Get or create Redis client for rate limiting."""
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    try:
        import redis as redis_sync
        _redis_client = redis_sync.from_url(_settings.redis_url, decode_responses=True)
        _redis_client.ping()
        return _redis_client
    except Exception as exc:
        logger.warning("Redis unavailable for rate limiting: %s", exc)
        return None


async def get_customer_phone(request: Request) -> Optional[str]:
    """Extract customer_phone from request body for per-customer rate limiting.
    
    Works for Charon's /reply endpoint where customer_phone is in the JSON body.
    Falls back to IP if no customer_phone found.
    """
    # Check if we already parsed it (middleware can set this)
    if hasattr(request.state, "customer_phone") and request.state.customer_phone:
        return request.state.customer_phone
    
    # For POST to /reply, parse the body
    if request.method == "POST" and "/reply" in request.url.path:
        try:
            body = await request.json()
            phone = body.get("customer_phone")
            if phone:
                request.state.customer_phone = phone
                return phone
        except Exception:
            pass
    
    return None


class CustomerRateLimiter:
    """Per-customer rate limiter using Redis INCR + TTL.
    
    Usage in router:
        @router.post("/reply")
        async def post_reply(request: Request, ...):
            allowed, remaining, reset = await customer_limiter.check(request)
            if not allowed:
                raise HTTPException(429, "Rate limit exceeded. Try again in a moment.")
    """
    
    def __init__(self, requests_per_minute: int = 5, burst: int = 3):
        self.requests_per_minute = requests_per_minute
        self.burst = burst  # Allow small bursts above the steady rate
    
    async def check(self, request: Request) -> tuple[bool, int, int]:
        """Check if request is allowed.
        
        Returns: (allowed, remaining_requests, seconds_until_reset)
        """
        phone = await get_customer_phone(request)
        if not phone:
            # No customer_phone — fall back to IP-based limit
            ip = get_remote_address(request)
            key = f"ratelimit:ip:{ip}"
        else:
            key = f"ratelimit:customer:{phone}"
        
        redis = _get_redis()
        if not redis:
            # Redis down — allow request (fail open for UX)
            return True, 999, 60
        
        try:
            pipe = redis.pipeline()
            now = redis.time()[0]  # Redis server time
            window = 60  # 1 minute window
            
            # Clean old entries and add current request
            pipe.zremrangebyscore(key, 0, now - window)
            pipe.zadd(key, {str(now): now})
            pipe.zcard(key)
            pipe.expire(key, window + 1)
            
            results = pipe.execute()
            current_count = results[2]  # zcard result
            
            allowed = current_count <= self.requests_per_minute
            remaining = max(0, self.requests_per_minute - current_count)
            
            # Find oldest entry in window to calculate reset
            oldest = redis.zrange(key, 0, 0, withscores=True)
            if oldest:
                reset = int(oldest[0][1]) + window - now
            else:
                reset = window
            
            return allowed, remaining, reset
            
        except Exception as exc:
            logger.warning("Rate limiter Redis error: %s", exc)
            return True, 999, 60  # Fail open


# Charon per-customer limiter: 5 requests/minute per customer
# With multi-tool loop (up to 3 LLM calls per message), this means
# ~1-2 customer messages per minute — reasonable for chat UX
customer_limiter = CustomerRateLimiter(requests_per_minute=5, burst=3)
