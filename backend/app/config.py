"""Bunche Backend Configuration"""
import os
from functools import lru_cache
from typing import List
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)
    database_url: str = "postgresql+asyncpg://user:password@localhost:5432/bunche"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = "your-jwt-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 15
    admin_token: str = "your-admin-token-change-in-production"
    flutterwave_secret_key: str = ""
    flutterwave_public_key: str = ""
    flutterwave_webhook_secret: str = ""
    whatsapp_access_token: str = ""
    whatsapp_phone_number_id: str = ""
    minimax_api_key: str = ""
    sentry_dsn: str = ""
    sentry_traces_sample_rate: float = 0.1
    cors_origins: str = "http://localhost:3000,https://bunche.ng"
    rate_limit_per_minute: int = 60
    log_level: str = "INFO"
    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str) -> List[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v
    @property
    def is_production(self) -> bool:
        return self.log_level.upper() in ("WARNING", "ERROR", "CRITICAL")
@lru_cache()
def get_settings() -> Settings:
    return Settings()
