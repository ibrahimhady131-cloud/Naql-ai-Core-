"""Telemetry Ingress FastAPI application."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, FastAPI, HTTPException, status
from sqlalchemy import desc, select
import paho.mqtt.client as mqtt

from naql_common.db.deps import CockroachSession, close_all, init_cockroach
from naql_common.db.models.telemetry import TruckPosition
from naql_common.geo import Coordinate

from .core.config import settings
from .processing.processor import MessageProcessor

processor = MessageProcessor(batch_size=settings.BATCH_SIZE)

api_router = APIRouter(prefix="/api/v1", tags=["telemetry"])

_mqtt_client: mqtt.Client | None = None


def on_mqtt_connect(client, userdata, flags, rc):
    """Callback when connected to MQTT broker."""
    if rc == 0:
        print(f"[MQTT] Connected to broker at {settings.MQTT_BROKER_HOST}:{settings.MQTT_BROKER_PORT}")
        # Subscribe to position topics
        client.subscribe("naql/telemetry/v1/+/pos")
        print("[MQTT] Subscribed to naql/telemetry/v1/+/pos")
    else:
        print(f"[MQTT] Connection failed with code {rc}")


# Global event loop reference for thread-safe async calls
_main_loop: asyncio.AbstractEventLoop | None = None


def on_mqtt_message(client, userdata, msg):
    """Callback when MQTT message received."""
    try:
        topic = msg.topic
        # Extract truck_id from topic: naql/telemetry/v1/{truck_id}/pos
        parts = topic.split("/")
        if len(parts) >= 4 and parts[-1] == "pos":
            truck_id = parts[3]
            payload = json.loads(msg.payload.decode())

            # Save to database using global _cockroach
            from naql_common.db.deps import _cockroach
            if _cockroach and _main_loop is not None:
                lat = float(payload.get("lat", payload.get("latitude", 0)))
                lon = float(payload.get("lon", payload.get("longitude", 0)))
                speed = float(payload.get("speed", 0))

                coord = Coordinate(lat, lon)
                position = TruckPosition(
                    time=datetime.now(UTC),
                    truck_id=uuid.UUID(truck_id),
                    latitude=lat,
                    longitude=lon,
                    h3_index=coord.to_h3(),
                    speed_kmh=speed,
                    region_code="EG-CAI",
                )

                # Use thread-safe coroutine submission to main event loop
                async def save_position():
                    async for session in _cockroach.get_session():
                        session.add(position)
                        await session.commit()
                        break

                future = asyncio.run_coroutine_threadsafe(save_position(), _main_loop)
                try:
                    future.result(timeout=5)  # Wait max 5 seconds
                    print(f"[MQTT] Saved position for truck {truck_id}: ({lat}, {lon})")
                except Exception as db_err:
                    print(f"[MQTT] DB error: {db_err}")
            else:
                if _cockroach is None:
                    print(f"[MQTT] DB not initialized")
                if _main_loop is None:
                    print(f"[MQTT] Event loop not ready")
    except Exception as e:
        print(f"[MQTT] Error processing message: {e}")


async def start_mqtt_subscriber():
    """Start MQTT subscriber in background."""
    global _mqtt_client
    _mqtt_client = mqtt.Client(client_id=settings.MQTT_CLIENT_ID)
    _mqtt_client.on_connect = on_mqtt_connect
    _mqtt_client.on_message = on_mqtt_message

    try:
        _mqtt_client.connect(
            settings.MQTT_BROKER_HOST,
            settings.MQTT_BROKER_PORT,
            keepalive=60,
        )
        _mqtt_client.loop_start()
        print(f"[MQTT] Subscriber started, connecting to {settings.MQTT_BROKER_HOST}:{settings.MQTT_BROKER_PORT}")
    except Exception as e:
        print(f"[MQTT] Failed to connect: {e}")


@api_router.post("/ingest/position")
async def ingest_position(payload: dict) -> dict:
    """HTTP fallback for position ingestion (primary is MQTT)."""
    from .processing.processor import PositionMessage

    msg = PositionMessage(
        truck_id=payload["truck_id"],
        driver_id=payload.get("driver_id"),
        trip_id=payload.get("trip_id"),
        latitude=payload["latitude"],
        longitude=payload["longitude"],
        altitude_m=payload.get("altitude_m"),
        speed_kmh=payload.get("speed_kmh", 0.0),
        heading=payload.get("heading"),
        signal_strength=payload.get("signal_strength"),
        connection_type=payload.get("connection_type"),
        ignition_on=payload.get("ignition_on", True),
    )

    events = processor.process_position(msg)

    return {
        "received": True,
        "events_generated": len(events),
        "events": events,
        "buffer_size": processor.position_buffer_size,
    }


@api_router.post("/ingest/telemetry")
async def ingest_telemetry(payload: dict) -> dict:
    """HTTP fallback for telemetry ingestion (primary is MQTT)."""
    from .processing.processor import TelemetryMessage

    msg = TelemetryMessage(
        truck_id=payload["truck_id"],
        engine_rpm=payload.get("engine_rpm"),
        engine_temp_c=payload.get("engine_temp_c"),
        fuel_level_pct=payload.get("fuel_level_pct"),
        fuel_rate_lph=payload.get("fuel_rate_lph"),
        odometer_km=payload.get("odometer_km"),
        battery_voltage=payload.get("battery_voltage"),
        cargo_temp_c=payload.get("cargo_temp_c"),
        harsh_braking=payload.get("harsh_braking", False),
        harsh_acceleration=payload.get("harsh_acceleration", False),
        sharp_turn=payload.get("sharp_turn", False),
    )

    events = processor.process_telemetry(msg)

    return {
        "received": True,
        "events_generated": len(events),
        "events": events,
        "buffer_size": processor.telemetry_buffer_size,
    }


@api_router.get("/telemetry/stats")
async def get_stats() -> dict:
    """Get current telemetry processing statistics."""
    return {
        "position_buffer_size": processor.position_buffer_size,
        "telemetry_buffer_size": processor.telemetry_buffer_size,
    }


@api_router.post("/telemetry", status_code=status.HTTP_201_CREATED)
async def post_telemetry(payload: dict, session: CockroachSession) -> dict:
    """Persist a telemetry position update."""
    try:
        truck_id = uuid.UUID(payload["truck_id"])
        latitude = float(payload["latitude"])
        longitude = float(payload["longitude"])
        speed = float(payload.get("speed", payload.get("speed_kmh", 0.0)))
        fuel_level = payload.get("fuel_level", payload.get("fuel_level_pct"))
        fuel_level_f = float(fuel_level) if fuel_level is not None else None
        ts = payload.get("timestamp")
        time = (
            datetime.fromisoformat(ts.replace("Z", "+00:00"))
            if isinstance(ts, str)
            else datetime.now(UTC)
        )
        region_code = payload.get("region_code", "EG-CAI")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

    coord = Coordinate(latitude, longitude)
    position = TruckPosition(
        time=time,
        truck_id=truck_id,
        driver_id=uuid.UUID(payload["driver_id"]) if payload.get("driver_id") else None,
        trip_id=uuid.UUID(payload["trip_id"]) if payload.get("trip_id") else None,
        latitude=latitude,
        longitude=longitude,
        altitude_m=payload.get("altitude_m"),
        accuracy_m=payload.get("accuracy_m"),
        h3_index=coord.to_h3(),
        speed_kmh=speed,
        heading=payload.get("heading"),
        signal_strength=payload.get("signal_strength"),
        connection_type=payload.get("connection_type"),
        ignition_on=payload.get("ignition_on", True),
        region_code=region_code,
    )

    session.add(position)
    await session.commit()

    return {
        "received": True,
        "truck_id": str(truck_id),
        "time": time.isoformat(),
        "h3_index": position.h3_index,
        "speed": speed,
        "fuel_level": fuel_level_f,
    }


@api_router.get("/telemetry/truck/{truck_id}")
async def get_latest_positions(truck_id: str, session: CockroachSession, limit: int = 10) -> dict:
    """Get latest positions for a truck."""
    tid = uuid.UUID(truck_id)
    stmt = (
        select(TruckPosition)
        .where(TruckPosition.truck_id == tid)
        .order_by(desc(TruckPosition.time))
        .limit(limit)
    )
    rows = (await session.execute(stmt)).scalars().all()
    return {
        "truck_id": truck_id,
        "count": len(rows),
        "positions": [
            {
                "timestamp": r.time.isoformat(),
                "latitude": r.latitude,
                "longitude": r.longitude,
                "speed": r.speed_kmh,
                "fuel_level": None,
                "h3_index": r.h3_index,
                "region_code": r.region_code,
            }
            for r in rows
        ],
    }


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Application lifecycle manager."""
    global _main_loop
    print(f"Starting {settings.SERVICE_NAME} on port {settings.SERVICE_PORT}")
    print(f"MQTT Broker: {settings.MQTT_BROKER_HOST}:{settings.MQTT_BROKER_PORT}")
    if not settings.DATABASE_URL or settings.DATABASE_URL == "sqlite://":
        msg = "Telemetry Ingress requires DATABASE_URL"
        raise RuntimeError(msg)

    init_cockroach(settings.DATABASE_URL)
    print(f"  Connected to database: {settings.DATABASE_URL.split('@')[-1]}")

    # Store reference to the running event loop for thread-safe MQTT callbacks
    _main_loop = asyncio.get_event_loop()

    # Start MQTT subscriber in background
    await start_mqtt_subscriber()

    yield
    if _mqtt_client:
        _mqtt_client.loop_stop()
        _mqtt_client.disconnect()
    await close_all()
    _main_loop = None
    print(f"Shutting down {settings.SERVICE_NAME}")


app = FastAPI(
    title="Naql.ai Telemetry Ingress",
    description="MQTT telemetry ingestion and real-time stream processing",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(api_router)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy", "service": settings.SERVICE_NAME}
