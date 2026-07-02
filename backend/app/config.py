"""Bunche Backend Configuration"""
import os
from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Database
    database_url: str = "postgresql+asyncpg://user:password@localhost:5432/bunche"
    redis_url: str = "redis://localhost:6379/0"

    # JWT
    jwt_secret: str = "your-jwt-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 15

    # Admin
    admin_token: str = "your-admin-token-change-in-production"

    # Flutterwave
    flutterwave_secret_key: str = ""
    flutterwave_public_key: str = ""
    flutterwave_webhook_secret: str = ""

    # WhatsApp
    whatsapp_access_token: str = ""
    whatsapp_phone_number_id: str = ""

    # Minimax
    minimax_api_key: str = ""

    # Sentry
    sentry_dsn: str = ""
    sentry_traces_sample_rate: float = 0.1

    # CORS
    cors_origins: List[str] = ["http://localhost:3000", "https://bunche.ng"]

    # Rate Limiting
    rate_limit_per_minute: int = 60

    # Logging
    log_level: str = "INFO"

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.log_level.upper() in ("WARNING", "ERROR", "CRITICAL")


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
