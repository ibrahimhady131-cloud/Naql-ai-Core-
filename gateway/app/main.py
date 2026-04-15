"""GraphQL Gateway FastAPI application."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from strawberry.fastapi import GraphQLRouter

from .graphql import schema as _schema_mod
from .graphql.schema import schema


def _parse_cors_origins() -> list[str]:
    """Parse GATEWAY_CORS_ORIGINS env var into a list of allowed origins."""
    raw = os.getenv("GATEWAY_CORS_ORIGINS", "http://localhost:3000,http://localhost:5000")
    return [o.strip() for o in raw.split(",") if o.strip()]


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Application lifecycle manager."""
    print("Starting Naql.ai GraphQL Gateway on port 4000")
    yield
    # Close the shared httpx client on shutdown
    from .graphql.schema import get_service_client
    client = get_service_client()
    client.close()
    print("Shutting down GraphQL Gateway")


app = FastAPI(
    title="Naql.ai GraphQL Gateway",
    description="Unified GraphQL API for the Naql.ai logistics ecosystem",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware for mobile/web clients
# Disable credentials when wildcard origins are used to prevent CSRF attacks.
_cors_origins = _parse_cors_origins()
_allow_creds = "*" not in _cors_origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=_allow_creds,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount GraphQL endpoint
graphql_app = GraphQLRouter(schema)
app.include_router(graphql_app, prefix="/graphql")


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy", "service": "graphql-gateway"}
