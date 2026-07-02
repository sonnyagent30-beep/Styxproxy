"""Test configuration — must be imported before anything else."""
import os

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
