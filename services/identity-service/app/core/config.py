"""Identity Service configuration."""

from __future__ import annotations

import os

from pydantic_settings import BaseSettings


def _db_url() -> str:
    """Fall back to Replit PostgreSQL if no service-specific URL is configured."""
    return os.getenv("DATABASE_URL") or ""


class Settings(BaseSettings):
    """Identity service settings loaded from environment variables."""

    SERVICE_NAME: str = "identity-service"
    SERVICE_PORT: int = 8001
    GRPC_PORT: int = 50051
    DEBUG: bool = False

    DATABASE_URL: str = _db_url()

    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    NATS_URL: str = "nats://localhost:4222"
    REDIS_URL: str = "redis://localhost:6379/0"

    model_config = {"env_prefix": "IDENTITY_", "env_file": ".env", "extra": "ignore"}


settings = Settings()
