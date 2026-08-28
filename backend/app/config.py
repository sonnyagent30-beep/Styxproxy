"""Styxproxy Backend Configuration"""

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
    database_url: str = "postgresql+asyncpg://user:password@localhost:5432/styxproxy"

    # ── JWT (required for auth to work) ─────────────────────────────────────
    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 15

    # ── Credential Encryption (Fernet key for at-rest field encryption) ────
    # Used to encrypt styxproxy_password (proxy auth tokens) at rest.
    # Generate with: python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    # Leave empty to disable (NOT RECOMMENDED in production).
    cred_encryption_key: str = ""

    # ── Admin ───────────────────────────────────────────────────────────────
    admin_token: str = ""

    # ── Flutterwave (required for payments) ─────────────────────────────────
    flutterwave_secret_key: str = ""
    # FLWPUBK-TEST (Flutterwave test public key); override via FLUTTERWAVE_PUBLIC_KEY in .env when going live
    flutterwave_public_key: str = "I14tjXLvFqcs4eCcaDW1BeY22XJaaLre"
    flutterwave_webhook_secret: str = ""

    # ── Additional payment gateways (optional) ──────────────────────────────
    paystack_secret_key: str = ""
    nowpayments_api_key: str = ""
    nowpayments_ipn_secret: str = ""
    nowpayments_base_url: str = "https://api.nowpayments.io"

    # ── WhatsApp (required for WhatsApp messaging) ──────────────────────────
    whatsapp_access_token: str = ""
    whatsapp_phone_number_id: str = ""

    # ── Minimax (required for AI features) ──────────────────────────────────
    minimax_api_key: str = ""

    # ── Groq (required for AI features) ─────────────────────────────────────
    groq_api_key: str = ""

    # ── Resend (required for email) ─────────────────────────────────────────
    resend_api_key: str = ""
    betterstack_api_key: str = ""
    betterstack_status_page_id: str = ""
    betterstack_monitor_id: str = ""
    betterstack_status_page_url: str = ""
    from_email: str = "Styxproxy <noreply@styxproxy.com>"
    support_email: str = "support@styxproxy.com"
    admin_email: str = "support@styxproxy.com"

    # ── Proxy Provider ───────────────────────────────────────────────────────
    # API credentials for the proxy provider (Proxy-Seller / DataImpulse / etc.)
    proxy_seller_api_key: str = ""
    proxy_seller_base_url: str = "https://api.proxy-seller.com"
    proxy_seller_balance_alert_threshold_usd: float = 10.0

    # ── DataImpulse (S1.2 — primary residential/mobile proxy provider) ──────
    # Used for trial credential creation in the Theorem Reach → trial pipeline.
    # Purchase at https://dataimpulse.com — $5 trial gives 5 GB residential.
    dataimpulse_api_key: str = ""

    # ── Decodo (S2.8 — secondary provider, city-level targeting) ────────────
    # Formerly Smartproxy. Used for Nigeria city-level targeting (Lagos, Abuja).
    # DataImpulse handles all other countries.
    # Sign up: https://decodo.com — $5 trial available.
    decodo_api_key: str = ""

    # ── 3proxy port allocation range ─────────────────────────────────────────
    # Allocated from this range when spinning up trial SOCKS5 ports.
    # Must not overlap with any other Dante/3proxy port allocation.
    threeproxy_port_range_start: int = 10000
    threeproxy_port_range_end: int = 50000

    # ── TheoremReach (survey completion → trial pipeline) ─────────────────────
    # Webhook secret for HMAC-SHA256 signature verification on the theorem-reach
    # webhook endpoint. Found in TheoremReach dashboard → integrations → webhooks.
    theorem_reach_webhook_secret: str = ""

    # ── Dante (branding gateway — runs on VPS) ───────────────────────────────
    dante_api_url: str = "http://localhost:9000"
    dante_api_key: str = ""
    dante_default_port: int = 1080

    # ── n8n Webhook (for automation triggers) ────────────────────────────────
    n8n_webhook_url: str = "https://n8n.styxproxy.com/webhook/credentials-delivered"

    # ── Sentry ───────────────────────────────────────────────────────────────
    sentry_dsn: str = ""
    sentry_traces_sample_rate: float = 0.1

    # ── CORS ────────────────────────────────────────────────────────────────
    # Verified Jul 28 18:13 UTC against live api.styxproxy.com CORS endpoints.
    # Removed: styxproxy-api-push.vercel.app (Vercel returns DEPLOYMENT_NOT_FOUND).
    # Removed duplicate 'https://styxproxy.com' in the list.
    # Kept: http://localhost:3000 only as a local-dev fallback; production
    # frontends must use https://styxproxy.com or https://www.styxproxy.com
    # (the www apex points to the same Vercel project as the apex).
    cors_origins: List[str] = [
        "http://localhost:3000",
        "https://styxproxy.com",
        "https://www.styxproxy.com",
        "https://api.styxproxy.com",
    ]  # + anything added via CORS_ORIGINS env var

    # ── Rate Limiting ───────────────────────────────────────────────────────
    rate_limit_per_minute: int = 60

    # ── Redis ───────────────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"

    # ── MiniMax-M2 cloud (Charon primary) ─────────────────────────────────
    # P0-5 (Jul 22 2026): M2 is the Charon primary. Endpoint is api.minimax.io.
    # Set MINIMAX_API_KEY in .env to enable.
    minimax_base_url: str = "https://api.minimax.io/v1"
    groq_base_url: str = "https://api.groq.com/openai/v1"

    # ── LiteLLM (Charon LLM proxy sidecar) ──────────────────────────────────
    # P0-5 (Jul 22 2026): required for the deep health endpoint to verify
    # the LLM stack is reachable. Both vars are read from the container env
    # at startup; defaults match the local-dev setup.
    litellm_base_url: str = "http://127.0.0.1:4000"
    litellm_api_key: str = "dev-placeholder-not-a-real-key"

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

        logger = logging.getLogger("app.config")

        # FAIL — app will not function without these
        failures: list[str] = []

        if not self.jwt_secret or self.jwt_secret == "your-jwt-secret-key-change-in-production":
            failures.append(
                "JWT_SECRET is still the default placeholder. Set JWT_SECRET to a secure value: openssl rand -base64 32"
            )

        if not self.admin_token or self.admin_token == "your-admin-token-change-in-production":
            failures.append("ADMIN_TOKEN is still the default placeholder. Set ADMIN_TOKEN to a secure value.")

        # PAY-1 CRITICAL (CVSS 8.1): flutterwave_webhook_secret must be set.
        # When absent/empty, verify_flutterwave_signature() uses an empty HMAC key,
        # making signature verification a no-op — any unsigned payload is accepted.
        if not self.flutterwave_webhook_secret:
            failures.append(
                "FLUTTERWAVE_WEBHOOK_SECRET is not set. "
                "This must be configured before any production payment traffic: "
                "find it in your Flutterwave dashboard under Settings > Webhooks."
            )

        # S2.3 (SEC finding): TheoremReach webhook has no signature verification.
        # Require THEOREM_REACH_WEBHOOK_SECRET so the HMAC check in the webhook
        # handler actually gates access. An empty string bypasses the check entirely.
        if not self.theorem_reach_webhook_secret:
            failures.append(
                "THEOREM_REACH_WEBHOOK_SECRET is not set. "
                "Theorem Reach survey webhooks will be rejected until this is configured: "
                "find it in your TheoremReach dashboard under Integrations > Webhooks."
            )

        # OPS-1 HIGH (STYXv2-003-SEC): OPS_JWT_SECRET must be set explicitly.
        # The ops_auth module already raises ValueError at import time if the env
        # var is absent, but we also enforce it here so the full validation error
        # message is visible at startup alongside other missing-config failures.
        import os as _os
        if not _os.environ.get("OPS_JWT_SECRET"):
            failures.append(
                "OPS_JWT_SECRET is not set. "
                "Financial ops endpoints (/refund, /reprocess) require an explicit "
                "OPS_JWT_SECRET. Set it to a secure value: openssl rand -base64 32"
            )

        if failures:
            raise ValueError("\n".join(failures))

        # WARN — database URL uses placeholder default; will use localhost
        if not self.database_url or self.database_url == "postgresql+asyncpg://user:password@localhost:5432/styxproxy":
            logger.warning(
                "DATABASE_URL is using the default placeholder value. "
                "Set DATABASE_URL to your PostgreSQL connection string."
            )

        # WARN — feature will be non-functional
        env_warnings: list[str] = []

        if not self.flutterwave_secret_key:
            env_warnings.append("FLUTTERWAVE_SECRET_KEY not set — payment processing is disabled")
        if not self.whatsapp_access_token:
            env_warnings.append("WHATSAPP_ACCESS_TOKEN not set — WhatsApp messaging is disabled")
        if not self.minimax_api_key:
            env_warnings.append("MINIMAX_API_KEY not set — AI features are disabled")
        if not self.resend_api_key:
            env_warnings.append("RESEND_API_KEY not set — email features are disabled")

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
