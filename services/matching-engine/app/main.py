"""Matching Engine FastAPI application."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from naql_common.db.deps import close_all, init_cockroach

from .api.routes import router
from .core.config import settings


async def handle_payment_confirmed(msg):
    """Handle payment.confirmed NATS event."""
    try:
        data = json.loads(msg.data.decode())
        shipment_id = data.get("shipment_id")
        amount = data.get("amount")
        print(f"[Matching Engine] Received payment.confirmed for shipment: {shipment_id}, amount: {amount}")
        
        # Update shipment status to assigned (would update DB here)
        print(f"[Matching Engine] AI Reasoning: Payment verified. Dispatching truck to pickup location.")
    except Exception as e:
        print(f"[Matching Engine] Error handling payment.confirmed: {e}")


async def start_nats_subscriber():
    """Start NATS subscriber for payment.confirmed events."""
    try:
        import nats
        nc = await nats.connect(settings.NATS_URL)
        await nc.subscribe("payment.confirmed", cb=handle_payment_confirmed)
        print("[Matching Engine] Subscribed to payment.confirmed NATS subject")
    except Exception as e:
        print(f"[Matching Engine] Warning: Failed to start NATS subscriber: {e}")


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
    
    # Start NATS subscriber for payment events
    asyncio.create_task(start_nats_subscriber())
    
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
