"""Test configuration — must be imported before anything else."""
import os
import asyncio
import pytest
import pytest_asyncio

# Set test mode FIRST — disables config validator's fail-fast on placeholder values
os.environ["TESTING"] = "1"

# Set test environment variables
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-not-real-32chars-long")
os.environ.setdefault("ADMIN_TOKEN", "test-admin-token-not-real")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://styxproxy:styxproxy@localhost:5432/styxproxy_test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("LOG_LEVEL", "DEBUG")
os.environ.setdefault("FLUTTERWAVE_SECRET_KEY", "test-flw-key")
os.environ.setdefault("FLUTTERWAVE_PUBLIC_KEY", "test-flw-pub")
os.environ.setdefault("FLUTTERWAVE_WEBHOOK_SECRET", "test-webhook-secret")
# Gateway webhook secrets for the other providers. Without these the verifiers
# short-circuit to False (empty secret) and every Paystack/NOWPayments test
# fails 401 on a signature that was never actually checked — a green suite that
# proves nothing. See tests/test_webhook_replay_window.py.
os.environ.setdefault("PAYSTACK_SECRET_KEY", "test-paystack-secret")
os.environ.setdefault("NOWPAYMENTS_IPN_SECRET", "test-nowpayments-ipn-secret")
os.environ.setdefault("WHATSAPP_ACCESS_TOKEN", "test-wa-token")
os.environ.setdefault("WHATSAPP_PHONE_NUMBER_ID", "test-phone-id")
os.environ.setdefault("MINIMAX_API_KEY", "test-minimax-key")
os.environ.setdefault("OPS_JWT_SECRET", "test-ops-jwt-secret-not-real-32chars")
os.environ.setdefault("THEOREM_REACH_WEBHOOK_SECRET", "test-theorem-webhook")

# Now clear the settings cache so new env values are picked up
from app.config import get_settings
get_settings.cache_clear()


@pytest_asyncio.fixture(autouse=True)
async def _dispose_engine_after_test():
    """Dispose the SQLAlchemy async engine after each test.

    pytest-asyncio creates a fresh event loop per test, but the global async
    engine's pool holds connections bound to the previous loop. Without this
    fixture, the second test that touches the DB sees
    RuntimeError: Event loop is closed".
    """
    yield
    try:
        from app.database import engine
        await engine.dispose()
    except Exception:
        pass


@pytest.fixture(autouse=True)
def _disable_rate_limiting():
    """Disable the global slowapi limiter for the whole test session.

    The app installs a default limit of rate_limit_per_minute (60) keyed on the
    remote address. Every test client connects from 127.0.0.1, so all tests
    share ONE bucket, and the limiter's storage is the live Redis instance —
    meaning the bucket survives between test runs.

    The result is a test suite whose pass/fail depends on wall-clock timing and
    on whatever else has recently hit the API from this host: a file with enough
    request-posting tests starts returning 429 partway through, and the cutoff
    moves depending on machine speed. Observed directly — the same unmodified
    file produced 45 passed, then 7 failed, then 10 failed on three consecutive
    runs.

    No test asserts rate-limit behaviour, so nothing is lost by disabling it. A
    test that needs the limiter must re-enable it explicitly rather than relying
    on the suite happening to stay under the limit.
    """
    from app.limiter import limiter

    # `enabled` is assigned inside slowapi's Limiter.__init__ rather than
    # declared on the class, so type checkers cannot see it. It is the
    # documented off-switch, checked by Limiter.hit / the middleware.
    previous = getattr(limiter, "enabled", True)
    setattr(limiter, "enabled", False)
    try:
        yield
    finally:
        setattr(limiter, "enabled", previous)
