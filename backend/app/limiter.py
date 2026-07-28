"""Rate limiter instance — imported by routers, not main (avoids circular import).

Theme A: storage backend is Redis so counters are shared across uvicorn workers.
Without this, the default in-memory storage makes the per-IP limit per-process
(N workers → effective limit = N × declared limit). Redis-backed moving-window
limiters are the standard fix.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import get_settings

_settings = get_settings()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[f"{_settings.rate_limit_per_minute}/minute"],
    # Shared across all workers when running with --workers > 1.
    storage_uri=_settings.redis_url,
    # Use the "moving-window" strategy so the window slides continuously
    # rather than resetting on a fixed boundary. Matches admin-workflow
    # expectations ("10 in 5 minutes" == any 5-minute window).
    strategy="moving-window",
)
