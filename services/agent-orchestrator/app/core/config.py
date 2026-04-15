"""Agent Orchestrator configuration."""

from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Agent orchestrator settings."""

    SERVICE_NAME: str = "agent-orchestrator"
    SERVICE_PORT: int = 8005
    GRPC_PORT: int = 50055
    DEBUG: bool = False

    # LLM
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"
    OPENAI_TEMPERATURE: float = 0.1

    # Vector DB (Pinecone)
    PINECONE_API_KEY: str = ""
    PINECONE_INDEX_NAME: str = "naql-agent-memory"
    PINECONE_ENVIRONMENT: str = "us-east-1"

    # Internal service URLs
    IDENTITY_SERVICE_URL: str = "http://localhost:8001"
    FLEET_SERVICE_URL: str = "http://localhost:8002"
    MATCHING_SERVICE_URL: str = "http://localhost:8003"
    FINTRACK_SERVICE_URL: str = "http://localhost:8004"

    # NATS
    NATS_URL: str = "nats://localhost:4222"

    # Agent behavior
    MAX_PLANNING_STEPS: int = 10
    AGENT_TIMEOUT_SEC: int = 60
    ENABLE_SENTINEL: bool = True

    # LLM Mode: Set to "true" to use real LLM, "false" for logic-based mode
    USE_REAL_LLM: bool = False

    model_config = {"env_prefix": "AGENT_", "env_file": ".env"}


settings = Settings()
