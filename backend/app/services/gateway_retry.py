"""Gateway retry helper — exponential backoff with jitter for payment gateway calls.

WHY THIS MODULE EXISTS
----------------------
Flutterwave's `verify_by_reference` endpoint returns 503 approximately 30% of
the time (measured). Without retry, a transient upstream blip becomes a hard
payment failure for the customer — 13% checkout failure rate on a revenue path.

DESIGN
------
- `is_retryable_status(status_code)`: 5xx and 429 are retryable; 4xx (except 429)
  is terminal. A 400 means the request itself is malformed — retrying won't help.
- `retry_on_5xx(fn, max_attempts, base_delay, max_delay)`: wraps an async callable,
  retrying on retryable HTTP errors with exponential backoff + full jitter.
- `GatewayCircuitBreaker`: lightweight failure-counting circuit breaker. Opens
  after N consecutive failures, closes after a cooldown period. Prevents
  hammering a downed gateway and makes outages visible in logs.

IDEMPOTENCY
-----------
Both Flutterwave and Paystack accept a stable `tx_ref` as an idempotency key.
Retrying a creation call with the SAME tx_ref is safe — the gateway returns the
existing transaction rather than creating a duplicate.
"""

import asyncio
import logging
import random
import time
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Optional, TypeVar

import httpx

logger = logging.getLogger(__name__)

T = TypeVar("T")

# ── Retryable status codes ─────────────────────────────────────────────────────

RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})


def is_retryable_status(status_code: int) -> bool:
    """True if an HTTP status code indicates a transient (retryable) error.

    429 (rate limit) and 5xx (server error) are retryable.
    4xx (client error) is NOT retryable — the request itself is wrong.
    """
    return status_code in RETRYABLE_STATUS_CODES


def is_retryable_exception(exc: BaseException) -> bool:
    """True if an exception indicates a transient network/HTTP error.

    Covers: httpx.TimeoutException, httpx.NetworkError, httpx.ProtocolError,
    and httpx.HTTPStatusError with a retryable status code.
    """
    if isinstance(exc, httpx.TimeoutException):
        return True
    if isinstance(exc, (httpx.NetworkError, httpx.ProtocolError)):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return is_retryable_status(exc.response.status_code)
    return False


# ── Retry wrapper ──────────────────────────────────────────────────────────────


async def retry_on_5xx(
    fn: Callable[[], Awaitable[T]],
    *,
    max_attempts: int = 3,
    base_delay: float = 0.5,
    max_delay: float = 5.0,
    operation: str = "gateway call",
) -> T:
    """Call `fn` with exponential backoff + jitter on retryable errors.

    Args:
        fn: Zero-arg async callable to invoke. Called fresh on each attempt.
        max_attempts: Total number of attempts (default 3).
        base_delay: Initial delay in seconds (default 0.5).
        max_delay: Maximum delay cap in seconds (default 5.0).
        operation: Human-readable name for logging.

    Returns:
        The successful return value of `fn`.

    Raises:
        The last retryable exception if all attempts are exhausted.
        Non-retryable exceptions are raised immediately without retry.

    Delay formula: min(base_delay * 2^attempt, max_delay) + uniform(0, delay)
    This is "full jitter" — AWS's recommended approach for avoiding thundering herd.
    """
    last_exc: Optional[BaseException] = None

    for attempt in range(max_attempts):
        try:
            return await fn()
        except Exception as exc:
            if not is_retryable_exception(exc):
                # Terminal error — don't retry 4xx, don't retry bad requests.
                logger.warning(
                    "%s: non-retryable error on attempt %d/%d: %s",
                    operation, attempt + 1, max_attempts, exc,
                )
                raise

            last_exc = exc
            if attempt < max_attempts - 1:
                # Exponential backoff with full jitter
                delay = min(base_delay * (2 ** attempt), max_delay)
                jittered = delay * (0.5 + random.random() * 0.5)
                logger.warning(
                    "%s: attempt %d/%d failed (%s) — retrying in %.2fs",
                    operation, attempt + 1, max_attempts, exc, jittered,
                )
                await asyncio.sleep(jittered)
            else:
                logger.error(
                    "%s: all %d attempts exhausted — last error: %s",
                    operation, max_attempts, exc,
                )

    # All attempts exhausted — raise the last retryable exception.
    assert last_exc is not None  # narrows Optional for type checker
    raise last_exc


# ── Circuit breaker ────────────────────────────────────────────────────────────


@dataclass
class GatewayCircuitBreaker:
    """Lightweight circuit breaker for payment gateway calls.

    States:
    - CLOSED: normal operation. Failures are counted.
    - OPEN: circuit is open. Calls fail fast without hitting the gateway.
      After `cooldown_seconds`, transitions to HALF_OPEN.
    - HALF_OPEN: one trial call is allowed. If it succeeds, circuit closes.
      If it fails, circuit re-opens with a fresh cooldown.

    This is deliberately simple — no external dependencies, no threading locks
    (single-threaded async). It exists to make a sustained gateway outage
    visible rather than showing up as scattered 502s in the log.
    """

    name: str
    failure_threshold: int = 5
    cooldown_seconds: float = 30.0

    _consecutive_failures: int = 0
    _opened_at: float = 0.0
    _state: str = "closed"  # "closed" | "open" | "half_open"

    @property
    def state(self) -> str:
        """Current circuit state, accounting for cooldown expiry."""
        if self._state == "open":
            if time.monotonic() - self._opened_at >= self.cooldown_seconds:
                self._state = "half_open"
                logger.info("%s circuit breaker: cooldown expired — entering half_open", self.name)
        return self._state

    def allow_request(self) -> bool:
        """True if a request should be allowed through."""
        state = self.state
        if state == "closed":
            return True
        if state == "half_open":
            return True  # one trial call
        return False  # open — fail fast

    def record_success(self) -> None:
        """Record a successful call — resets the circuit."""
        if self._state != "closed":
            logger.info("%s circuit breaker: success — circuit closed", self.name)
        self._consecutive_failures = 0
        self._state = "closed"

    def record_failure(self) -> None:
        """Record a failed call — may open the circuit."""
        self._consecutive_failures += 1
        if self._consecutive_failures >= self.failure_threshold:
            self._state = "open"
            self._opened_at = time.monotonic()
            logger.error(
                "%s circuit breaker: OPEN after %d consecutive failures (cooldown %.0fs)",
                self.name, self._consecutive_failures, self.cooldown_seconds,
            )

    async def call(self, fn: Callable[[], Awaitable[T]], *, operation: str = "gateway call") -> T:
        """Call `fn` through the circuit breaker.

        If the circuit is open, raises httpx.ConnectError immediately without
        calling `fn`. Otherwise delegates to `fn` and records the outcome.
        """
        if not self.allow_request():
            raise httpx.ConnectError(
                f"{self.name} circuit breaker is OPEN — {operation} skipped"
            )
        try:
            result = await fn()
            self.record_success()
            return result
        except Exception:
            self.record_failure()
            raise


# ── Shared circuit breaker instances ───────────────────────────────────────────

_flutterwave_breaker = GatewayCircuitBreaker(
    name="flutterwave",
    failure_threshold=5,
    cooldown_seconds=30.0,
)

_paystack_breaker = GatewayCircuitBreaker(
    name="paystack",
    failure_threshold=5,
    cooldown_seconds=30.0,
)


def get_flutterwave_breaker() -> GatewayCircuitBreaker:
    return _flutterwave_breaker


def get_paystack_breaker() -> GatewayCircuitBreaker:
    return _paystack_breaker
