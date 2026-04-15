"""Database connection management — supports Replit PostgreSQL, CockroachDB, and TimescaleDB."""

from __future__ import annotations

from collections.abc import AsyncGenerator
import ssl
import certifi
import os
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def _normalize_dsn(dsn: str) -> tuple[str, dict]:
    """Convert any PostgreSQL URL variant to asyncpg-compatible form.

    Handles:
    - Replit's postgresql://... → postgresql+asyncpg://...
    - Strips sslmode=disable/require query params (asyncpg uses connect_args)
    - Returns (normalized_url, connect_args)
    """
    url = dsn

    # Replace plain postgresql:// with asyncpg driver
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)

    connect_args: dict = {}

    parts = urlsplit(url)
    query_items = dict(parse_qsl(parts.query, keep_blank_values=True))

    if query_items.get("pgbouncer") == "true":
        connect_args["statement_cache_size"] = 0
        query_items.pop("pgbouncer", None)
    if "pooler.supabase.com" in parts.netloc:
        connect_args["statement_cache_size"] = 0

    if query_items.get("sslmode") == "require":
        ca_file = os.environ.get("NAQL_SSL_CA_FILE")
        cafile = ca_file or certifi.where()
        connect_args["ssl"] = ssl.create_default_context(cafile=cafile)
        query_items.pop("sslmode", None)
    elif query_items.get("sslmode") == "disable":
        query_items.pop("sslmode", None)

    new_query = urlencode(query_items, doseq=True)
    url = urlunsplit((parts.scheme, parts.netloc, parts.path, new_query, parts.fragment))

    # Strip trailing ?
    if url.endswith("?"):
        url = url[:-1]

    return url, connect_args


class DatabaseManager:
    """Manages async database connections."""

    def __init__(self, dsn: str, *, pool_size: int = 20, max_overflow: int = 10) -> None:
        normalized_dsn, connect_args = _normalize_dsn(dsn)
        self.engine: AsyncEngine = create_async_engine(
            normalized_dsn,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_pre_ping=True,
            echo=False,
            connect_args=connect_args,
        )
        self.session_factory = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Yield a database session with automatic cleanup."""
        async with self.session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def close(self) -> None:
        """Dispose of the engine connection pool."""
        await self.engine.dispose()


class CockroachDB(DatabaseManager):
    """CockroachDB / PostgreSQL transactional data manager."""

    def __init__(self, dsn: str) -> None:
        super().__init__(dsn, pool_size=10, max_overflow=5)


class TimescaleDB(DatabaseManager):
    """TimescaleDB / PostgreSQL time-series data manager."""

    def __init__(self, dsn: str) -> None:
        super().__init__(dsn, pool_size=10, max_overflow=5)
