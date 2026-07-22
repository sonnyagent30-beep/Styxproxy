"""Test configuration — must be imported before anything else."""
import os
import asyncio
import pytest_asyncio

# Set test mode FIRST — disables config validator's fail-fast on placeholder values
os.environ["TESTING"] = "1"

# Set test environment variables
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-not-real-32chars-long")
os.environ.setdefault("ADMIN_TOKEN", "test-admin-token-not-real")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://bunche:bunche@localhost:5432/bunche_test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("LOG_LEVEL", "DEBUG")
os.environ.setdefault("FLUTTERWAVE_SECRET_KEY", "test-flw-key")
os.environ.setdefault("FLUTTERWAVE_PUBLIC_KEY", "test-flw-pub")
os.environ.setdefault("FLUTTERWAVE_WEBHOOK_SECRET", "test-webhook-secret")
os.environ.setdefault("WHATSAPP_ACCESS_TOKEN", "test-wa-token")
os.environ.setdefault("WHATSAPP_PHONE_NUMBER_ID", "test-phone-id")
os.environ.setdefault("MINIMAX_API_KEY", "test-minimax-key")

# Now clear the settings cache so new env values are picked up
from app.config import get_settings
get_settings.cache_clear()


@pytest_asyncio.fixture(autouse=True)
async def _dispose_engine_after_test():
    """Dispose the SQLAlchemy async engine after each test.

    pytest-asyncio creates a fresh event loop per test, but the global async
    engine's pool holds connections bound to the previous loop. Without this
    fixture, the second test that touches the DB sees
    RuntimeError("Event loop is closed").
    """
    yield
    try:
        from app.database import engine
        await engine.dispose()
    except Exception:
        pass
