"""Telemetry Ingress configuration."""

from __future__ import annotations

import os

from pydantic_settings import BaseSettings


def _db_url() -> str:
    """Use only DATABASE_URL - no fallback."""
    return os.getenv("DATABASE_URL") or ""


class Settings(BaseSettings):
    """Telemetry ingress settings."""

    SERVICE_NAME: str = "telemetry-ingress"
    SERVICE_PORT: int = 8006
    DEBUG: bool = False

    # MQTT (EMQX)
    MQTT_BROKER_HOST: str = "localhost"
    MQTT_BROKER_PORT: int = 1883
    MQTT_USERNAME: str = ""
    MQTT_PASSWORD: str = ""
    MQTT_CLIENT_ID: str = "naql-telemetry-ingress"

    # Topics
    MQTT_TOPIC_POSITION: str = "naql/truck/+/position"
    MQTT_TOPIC_TELEMETRY: str = "naql/truck/+/telemetry"
    MQTT_TOPIC_ALERT: str = "naql/truck/+/alert"

    # Database (Timescale if available; otherwise standard Postgres table)
    DATABASE_URL: str = _db_url()

    # Redis (for real-time geo index)
    REDIS_URL: str = "redis://localhost:6379/4"

    # NATS
    NATS_URL: str = "nats://localhost:4222"

    # Processing
    BATCH_SIZE: int = 100
    FLUSH_INTERVAL_SEC: int = 5
    GEOFENCE_CHECK_ENABLED: bool = True

    model_config = {"env_prefix": "TELEMETRY_", "env_file": ".env"}


settings = Settings()
