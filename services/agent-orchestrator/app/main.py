"""Agent Orchestrator FastAPI application."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .api.routes import router
from .core.config import settings
from .tools.service_tools import service_client


async def start_nats_subscriber():
    """Start NATS subscriber for shipment events."""
    try:
        from naql_common.events import EventBus, DomainEvent, EventType

        event_bus = EventBus()
        await event_bus.connect()
        print(f"[Agent] Connected to NATS EventBus")

        # Subscribe to shipment.created events
        sub = await event_bus._js.subscribe("shipment.created", durable="agent-shipment-processor")
        print(f"[Agent] Subscribed to shipment.created on NATS")

        async for msg in sub.messages:
            try:
                event = DomainEvent.from_bytes(msg.data)
                payload = event.payload
                shipment_id = payload.get("shipment_id", "unknown")
                pickup_h3 = payload.get("pickup_h3", "")
                dropoff_h3 = payload.get("dropoff_h3", "")
                cargo_type = payload.get("cargo_type", "")

                print(f"AI Brain: Received new shipment task. Starting logistics planning for ID: {shipment_id}")
                print(f"  -> Pickup H3: {pickup_h3}, Dropoff H3: {dropoff_h3}, Cargo: {cargo_type}")

                # Trigger LangGraph agent for autonomous planning
                try:
                    from .logic.graph import run_agent_for_shipment

                    result = await run_agent_for_shipment(
                        shipment_id=shipment_id,
                        pickup_h3=pickup_h3,
                        dropoff_h3=dropoff_h3,
                        cargo_type=cargo_type,
                    )

                    if result.get("selected_truck_id"):
                        print(f"[Agent] FINAL RECOMMENDATION: Match shipment {shipment_id} to truck {result['selected_truck_id']}")
                    else:
                        print(f"[Agent] No suitable truck found for shipment {shipment_id}")

                except Exception as agent_err:
                    print(f"[Agent] Error running agent graph: {agent_err}")

                await msg.ack()
            except Exception as e:
                print(f"[Agent] Error processing message: {e}")

    except Exception as e:
        print(f"[Agent] NATS subscriber error: {e}")


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Application lifecycle manager."""
    print(f"Starting {settings.SERVICE_NAME} on port {settings.SERVICE_PORT}")
    print(f"LLM Model: {settings.OPENAI_MODEL}")
    print(f"Sentinel enabled: {settings.ENABLE_SENTINEL}")

    # Start NATS subscriber in background
    nats_task = asyncio.create_task(start_nats_subscriber())

    yield
    # Cleanup
    nats_task.cancel()
    try:
        await nats_task
    except asyncio.CancelledError:
        pass
    await service_client.close()
    print(f"Shutting down {settings.SERVICE_NAME}")


app = FastAPI(
    title="Naql.ai Agent Orchestrator",
    description="LangGraph-powered AI agent for autonomous logistics orchestration",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(router)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy", "service": settings.SERVICE_NAME}
