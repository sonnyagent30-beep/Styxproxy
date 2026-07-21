"""Bunche Backend Configuration"""
import os
from functools import lru_cache
from typing import List

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Required for startup ─────────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://user:password@localhost:5432/bunche"

    # ── JWT (required for auth to work) ─────────────────────────────────────
    jwt_secret: str = "your-jwt-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 15

    # ── Admin ───────────────────────────────────────────────────────────────
    admin_token: str = "your-admin-token-change-in-production"

    # ── Flutterwave (required for payments) ─────────────────────────────────
    flutterwave_secret_key: str = ""
    flutterwave_public_key: str = ""
    flutterwave_webhook_secret: str = ""

    # ── WhatsApp (required for WhatsApp messaging) ──────────────────────────
    whatsapp_access_token: str = ""
    whatsapp_phone_number_id: str = ""

    # ── Minimax (required for AI features) ──────────────────────────────────
    minimax_api_key: str = ""

    # ── Resend (required for email) ─────────────────────────────────────────
    resend_api_key: str = ""
    from_email: str = "Styxproxy <noreply@styxproxy.com>"
    admin_email: str = "oyebiyiayomide30@gmail.com"

    # ── Proxy Provider ───────────────────────────────────────────────────────
    # API credentials for the proxy provider (Proxy-Seller / DataImpulse / etc.)
    proxy_seller_api_key: str = ""
    proxy_seller_base_url: str = "https://api.proxy-seller.com"
    proxy_seller_balance_alert_threshold_usd: float = 10.0

    # ── Dante (branding gateway — runs on VPS) ───────────────────────────────
    dante_api_url: str = "http://localhost:9000"
    dante_api_key: str = ""
    dante_default_port: int = 1080

    # ── n8n Webhook (for automation triggers) ────────────────────────────────
    n8n_webhook_url: str = "https://n8n.bunche.ng/webhook/credentials-delivered"

    # ── Sentry ───────────────────────────────────────────────────────────────
    sentry_dsn: str = ""
    sentry_traces_sample_rate: float = 0.1

    # ── CORS ────────────────────────────────────────────────────────────────
    cors_origins: List[str] = ["http://localhost:3000", "https://bunche.ng"]

    # ── Rate Limiting ───────────────────────────────────────────────────────
    rate_limit_per_minute: int = 60

    # ── Redis ───────────────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"

    # ── Logging ─────────────────────────────────────────────────────────────
    log_level: str = "INFO"

    # ── Derived ────────────────────────────────────────────────────────────
    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.log_level.upper() in ("WARNING", "ERROR", "CRITICAL")

    @property
    def is_staging(self) -> bool:
        """Check if running in staging mode."""
        return self.log_level.upper() in ("DEBUG", "INFO") and not self.is_production

    # ── Validators ─────────────────────────────────────────────────────────
    @model_validator(mode="after")
    def validate_environment(self) -> "Settings":
        """Fail fast on missing or obviously wrong required settings.

        Called once at startup when get_settings() is first invoked.
        Warns on missing optional integration keys (Flutterwave, WhatsApp, Minimax).
        """
        import logging
        import warnings as _warnings_module

        logger = logging.getLogger("app.config")

        # FAIL — app will not function without these
        failures: list[str] = []

        if not self.jwt_secret or self.jwt_secret == "your-jwt-secret-key-change-in-production":
            failures.append(
                "JWT_SECRET is still the default placeholder. "
                "Set JWT_SECRET to a secure value: openssl rand -base64 32"
            )

        if not self.admin_token or self.admin_token == "your-admin-token-change-in-production":
            failures.append(
                "ADMIN_TOKEN is still the default placeholder. "
                "Set ADMIN_TOKEN to a secure value."
            )

        if failures:
            raise ValueError("\n".join(failures))

        # WARN — database URL uses placeholder default; will use localhost
        if not self.database_url or self.database_url == "postgresql+asyncpg://user:password@localhost:5432/bunche":
            logger.warning(
                "DATABASE_URL is using the default placeholder value. "
                "Set DATABASE_URL to your PostgreSQL connection string."
            )

        # WARN — feature will be non-functional
        env_warnings: list[str] = []

        if not self.flutterwave_secret_key:
            env_warnings.append(
                "FLUTTERWAVE_SECRET_KEY not set — payment processing is disabled"
            )
        if not self.whatsapp_access_token:
            env_warnings.append(
                "WHATSAPP_ACCESS_TOKEN not set — WhatsApp messaging is disabled"
            )
        if not self.minimax_api_key:
            env_warnings.append(
                "MINIMAX_API_KEY not set — AI features are disabled"
            )
        if not self.resend_api_key:
            env_warnings.append(
                "RESEND_API_KEY not set — email features are disabled"
            )

        if env_warnings:
            for w in env_warnings:
                logger.warning(f"Environment warning: {w}")

        return self

    @field_validator("jwt_expire_minutes")
    @classmethod
    def jwt_expire_minutes_range(cls, v: int) -> int:
        if v < 1:
            raise ValueError("jwt_expire_minutes must be at least 1")
        if v > 60 * 24 * 7:
            raise ValueError("jwt_expire_minutes must be at most 10080 (7 days)")
        return v

    @field_validator("rate_limit_per_minute")
    @classmethod
    def rate_limit_range(cls, v: int) -> int:
        if v < 1:
            raise ValueError("rate_limit_per_minute must be at least 1")
        if v > 10000:
            raise ValueError("rate_limit_per_minute must be at most 10000")
        return v

    @field_validator("log_level")
    @classmethod
    def log_level_valid(cls, v: str) -> str:
        valid = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in valid:
            raise ValueError(f"log_level must be one of {valid}, got {v}")
        return v.upper()

    @field_validator("cors_origins", mode="before")
    @classmethod
    def cors_origins_parse(cls, v):
        """Accept both list and comma-separated string."""
        if isinstance(v, str):
            import ast
            try:
                return ast.literal_eval(v)
            except Exception:
                return [o.strip() for o in v.split(",") if o.strip()]
        return v


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance.

    First call runs all validators and may raise ValueError if required
    environment variables are missing or misconfigured.
    """
    return Settings()
