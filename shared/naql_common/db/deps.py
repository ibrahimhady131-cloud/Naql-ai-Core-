"""Database dependency injection for services.

Provides FastAPI-compatible dependency functions that yield
async database sessions from the appropriate connection manager.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from naql_common.db import CockroachDB, TimescaleDB

# Global connection managers — initialized per-service in lifespan
_cockroach: CockroachDB | None = None
_timescale: TimescaleDB | None = None


def init_cockroach(dsn: str) -> CockroachDB:
    """Initialize the CockroachDB connection manager (call once at startup)."""
    global _cockroach
    _cockroach = CockroachDB(dsn)
    return _cockroach


def init_timescale(dsn: str) -> TimescaleDB:
    """Initialize the TimescaleDB connection manager (call once at startup)."""
    global _timescale
    _timescale = TimescaleDB(dsn)
    return _timescale


async def get_cockroach_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield a CockroachDB session for transactional data."""
    if _cockroach is None:
        msg = "CockroachDB not initialized — call init_cockroach() in lifespan"
        raise RuntimeError(msg)
    async for session in _cockroach.get_session():
        yield session


async def get_timescale_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield a TimescaleDB session for time-series data."""
    if _timescale is None:
        msg = "TimescaleDB not initialized — call init_timescale() in lifespan"
        raise RuntimeError(msg)
    async for session in _timescale.get_session():
        yield session


async def close_all() -> None:
    """Dispose all database connections (call in shutdown)."""
    if _cockroach:
        await _cockroach.close()
    if _timescale:
        await _timescale.close()


# Type aliases for dependency injection
CockroachSession = Annotated[AsyncSession, Depends(get_cockroach_session)]
TimescaleSession = Annotated[AsyncSession, Depends(get_timescale_session)]
