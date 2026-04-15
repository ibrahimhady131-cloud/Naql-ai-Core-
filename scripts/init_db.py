"""Database initialization script — creates all tables in Replit PostgreSQL.

Run with:  python scripts/init_db.py
"""

from __future__ import annotations

import asyncio
import os
import ssl
import sys
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
 
import certifi

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "shared"))
from naql_common.db.base import Base

# Import all models so SQLAlchemy registers them
from naql_common.db.models.fintrack import (
    EscrowHold,
    Invoice,
    LedgerAccount,
    LedgerEntry,
    Transaction,
)
from naql_common.db.models.fleet import Truck, TruckMaintenance
from naql_common.db.models.identity import ApiKey, User, UserDocument
from naql_common.db.models.notification import Notification
from naql_common.db.models.shipment import (
    DriverPreferences,
    MatchHistory,
    Shipment,
    ShipmentAuditLog,
    Trip,
)
from naql_common.db.models.telemetry import DrivingViolation, GeofenceEvent

from sqlalchemy.ext.asyncio import create_async_engine

# Telemetry models need regular Postgres (not TimescaleDB hypertable setup here)
# TruckPosition and TruckTelemetry require TimescaleDB extensions — skip for now
# from naql_common.db.models.telemetry import TruckPosition, TruckTelemetry


async def init_db() -> None:
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL environment variable not set")
        sys.exit(1)

    connect_args: dict = {}

    parts = urlsplit(db_url)
    query_items = dict(parse_qsl(parts.query, keep_blank_values=True))

    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)

    if query_items.get("pgbouncer") == "true":
        connect_args["statement_cache_size"] = 0
        query_items.pop("pgbouncer", None)
    if "pooler.supabase.com" in db_url:
        connect_args["statement_cache_size"] = 0

    if query_items.get("sslmode") == "require":
        ca_file = os.environ.get("NAQL_SSL_CA_FILE")
        cafile = ca_file or certifi.where()
        connect_args["ssl"] = ssl.create_default_context(cafile=cafile)
        query_items.pop("sslmode", None)
    elif query_items.get("sslmode") == "disable":
        query_items.pop("sslmode", None)

    parts2 = urlsplit(db_url)
    new_query = urlencode(query_items, doseq=True)
    db_url = urlunsplit((parts2.scheme, parts2.netloc, parts2.path, new_query, parts2.fragment))

    print(f"Connecting to: {db_url.split('@')[-1]}")

    engine = create_async_engine(db_url, pool_pre_ping=True, echo=False, connect_args=connect_args)

    async with engine.begin() as conn:
        print("Creating all tables...")
        await conn.run_sync(Base.metadata.create_all)
        print("Done.")

    await engine.dispose()

    # Verify key tables
    from sqlalchemy import text
    engine2 = create_async_engine(db_url, pool_pre_ping=True, echo=False, connect_args=connect_args)
    async with engine2.connect() as conn:
        result = await conn.execute(
            text("SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename")
        )
        tables = [row[0] for row in result.fetchall()]
        print(f"\nTables in database ({len(tables)} total):")
        for t in tables:
            print(f"  ✓ {t}")
    await engine2.dispose()


if __name__ == "__main__":
    asyncio.run(init_db())
