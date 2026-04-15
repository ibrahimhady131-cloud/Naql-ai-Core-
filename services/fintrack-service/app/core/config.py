"""FinTrack Service configuration."""

from __future__ import annotations

import os

from pydantic_settings import BaseSettings


def _db_url() -> str:
    """Use only DATABASE_URL - no fallback."""
    return os.getenv("DATABASE_URL") or ""


class Settings(BaseSettings):
    """FinTrack service settings."""

    SERVICE_NAME: str = "fintrack-service"
    SERVICE_PORT: int = 8004
    GRPC_PORT: int = 50054
    DEBUG: bool = False

    DATABASE_URL: str = _db_url()
    NATS_URL: str = "nats://localhost:4222"
    REDIS_URL: str = "redis://localhost:6379/3"

    # Payment gateways
    FAWRY_API_KEY: str = ""
    FAWRY_SECRET: str = ""
    PAYMOB_API_KEY: str = ""
    PAYMOB_INTEGRATION_ID: str = ""

    # Pricing (2025 calibrated)
    SERVICE_FEE_PERCENTAGE: float = 0.08  # 8% platform fee
    INSURANCE_RATE_PER_KM: float = 1.5  # EGP per km (cargo insurance)
    BASE_FUEL_RATE_PER_KM: float = 14.0  # EGP per km (diesel, 2025 post-subsidy)

    model_config = {"env_prefix": "FINTRACK_", "env_file": ".env"}


settings = Settings()
