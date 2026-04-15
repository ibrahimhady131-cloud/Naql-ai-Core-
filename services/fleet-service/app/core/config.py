"""Fleet Service configuration."""

from __future__ import annotations

import os

from pydantic_settings import BaseSettings


def _db_url() -> str:
    """Fall back to Replit PostgreSQL if no service-specific URL is configured."""
    return os.getenv("DATABASE_URL") or ""


class Settings(BaseSettings):
    """Fleet service settings."""

    SERVICE_NAME: str = "fleet-service"
    SERVICE_PORT: int = 8002
    GRPC_PORT: int = 50052
    DEBUG: bool = False

    DATABASE_URL: str = _db_url()
    NATS_URL: str = "nats://localhost:4222"
    REDIS_URL: str = "redis://localhost:6379/1"

    TELEMETRY_BATCH_SIZE: int = 100
    POSITION_UPDATE_INTERVAL_SEC: int = 5

    model_config = {"env_prefix": "FLEET_", "env_file": ".env", "extra": "ignore"}


settings = Settings()
