"""Matching Engine FastAPI application."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from naql_common.db.deps import close_all, init_cockroach

from .api.routes import router
from .core.config import settings


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Application lifecycle manager."""
    print(f"Starting {settings.SERVICE_NAME} on port {settings.SERVICE_PORT}")
    if not settings.DATABASE_URL or settings.DATABASE_URL == "sqlite://":
        msg = "Matching Engine requires DATABASE_URL"
        raise RuntimeError(msg)

    db = init_cockroach(settings.DATABASE_URL)
    async with db.engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    print(f"  Connected to CockroachDB: {settings.DATABASE_URL.split('@')[-1]}")
    yield
    await close_all()
    print(f"Shutting down {settings.SERVICE_NAME}")


app = FastAPI(
    title="Naql.ai Matching Engine",
    description="Geo-spatial truck matching and driver assignment engine",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(router)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy", "service": settings.SERVICE_NAME}
