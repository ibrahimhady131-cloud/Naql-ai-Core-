"""Matching Engine configuration."""

from __future__ import annotations

import os

from pydantic_settings import BaseSettings


def _db_url() -> str:
    """Use only DATABASE_URL - no fallback."""
    return os.getenv("DATABASE_URL") or ""


class Settings(BaseSettings):
    """Matching engine settings."""

    SERVICE_NAME: str = "matching-engine"
    SERVICE_PORT: int = 8003
    GRPC_PORT: int = 50053
    DEBUG: bool = False

    DATABASE_URL: str = _db_url()
    NATS_URL: str = "nats://localhost:4222"
    REDIS_URL: str = "redis://localhost:6379/2"

    # Matching parameters
    DEFAULT_SEARCH_RADIUS_KM: float = 20.0
    MAX_SEARCH_RADIUS_KM: float = 100.0
    MAX_CANDIDATES: int = 10
    MATCH_TIMEOUT_SEC: int = 120

    # Scoring weights
    WEIGHT_DISTANCE: float = 0.30
    WEIGHT_RATING: float = 0.25
    WEIGHT_ETA: float = 0.25
    WEIGHT_PRICE: float = 0.20

    model_config = {"env_prefix": "MATCHING_", "env_file": ".env"}


settings = Settings()
