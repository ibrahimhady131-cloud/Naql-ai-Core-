"""TimescaleDB batch writer for telemetry data.

Flushes buffered position and telemetry messages from the
MessageProcessor into TimescaleDB hypertables using bulk inserts.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

import h3
from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession

from naql_common.db.models.telemetry import (
    DrivingViolation,
    GeofenceEvent,
    TruckPosition,
    TruckTelemetry,
)

from .processor import PositionMessage, TelemetryMessage

logger = logging.getLogger(__name__)


def _region_from_lat_lng(lat: float, lng: float) -> str:
    """Derive a rough Egyptian region code from coordinates."""
    if lat > 30.5:
        return "EG-ALX" if lng < 30.5 else "EG-DKH"
    if lat > 29.5:
        return "EG-CAI"
    if lat > 28.0:
        return "EG-SUE" if lng > 32 else "EG-FYM"
    return "EG-UEG"


async def flush_positions(
    session: AsyncSession, messages: list[PositionMessage]
) -> int:
    """Batch-insert position records into truck_positions hypertable."""
    if not messages:
        return 0

    rows = []
    for msg in messages:
        h3_index = h3.latlng_to_cell(msg.latitude, msg.longitude, 7)
        region = _region_from_lat_lng(msg.latitude, msg.longitude)
        rows.append(
            {
                "time": msg.timestamp,
                "truck_id": msg.truck_id,
                "driver_id": msg.driver_id,
                "trip_id": msg.trip_id,
                "latitude": msg.latitude,
                "longitude": msg.longitude,
                "altitude_m": msg.altitude_m,
                "accuracy_m": None,
                "h3_index": h3_index,
                "speed_kmh": msg.speed_kmh,
                "heading": msg.heading,
                "signal_strength": msg.signal_strength,
                "connection_type": msg.connection_type,
                "ignition_on": msg.ignition_on,
                "region_code": region,
            }
        )

    await session.execute(insert(TruckPosition), rows)
    await session.commit()
    logger.info("Flushed %d position records to TimescaleDB", len(rows))
    return len(rows)


async def flush_telemetry(
    session: AsyncSession, messages: list[TelemetryMessage]
) -> int:
    """Batch-insert telemetry records into truck_telemetry hypertable."""
    if not messages:
        return 0

    rows = []
    for msg in messages:
        rows.append(
            {
                "time": msg.timestamp,
                "truck_id": msg.truck_id,
                "engine_rpm": msg.engine_rpm,
                "engine_temp_c": msg.engine_temp_c,
                "fuel_level_pct": msg.fuel_level_pct,
                "fuel_rate_lph": msg.fuel_rate_lph,
                "odometer_km": msg.odometer_km,
                "battery_voltage": msg.battery_voltage,
                "dtc_codes": None,
                "check_engine": False,
                "cargo_temp_c": msg.cargo_temp_c,
                "ambient_temp_c": None,
                "humidity_pct": None,
                "harsh_braking": msg.harsh_braking,
                "harsh_acceleration": msg.harsh_acceleration,
                "sharp_turn": msg.sharp_turn,
                "region_code": "EG-CAI",
            }
        )

    await session.execute(insert(TruckTelemetry), rows)
    await session.commit()
    logger.info("Flushed %d telemetry records to TimescaleDB", len(rows))
    return len(rows)


async def write_geofence_event(
    session: AsyncSession,
    *,
    truck_id: str,
    trip_id: str | None,
    event_type: str,
    geofence_name: str,
    geofence_type: str,
    latitude: float,
    longitude: float,
    region_code: str | None = None,
) -> None:
    """Write a single geofence event to the geofence_events hypertable."""
    region = region_code or _region_from_lat_lng(latitude, longitude)
    await session.execute(
        insert(GeofenceEvent),
        [
            {
                "time": datetime.now(UTC),
                "truck_id": truck_id,
                "trip_id": trip_id,
                "event_type": event_type,
                "geofence_name": geofence_name,
                "geofence_type": geofence_type,
                "latitude": latitude,
                "longitude": longitude,
                "dwell_time_sec": None,
                "region_code": region,
            }
        ],
    )
    await session.commit()


async def write_driving_violation(
    session: AsyncSession,
    *,
    truck_id: str,
    driver_id: str,
    trip_id: str | None,
    violation_type: str,
    severity: str,
    speed_kmh: float | None = None,
    speed_limit_kmh: float | None = None,
    deviation_km: float | None = None,
    latitude: float,
    longitude: float,
    region_code: str | None = None,
) -> None:
    """Write a driving violation to the driving_violations hypertable."""
    region = region_code or _region_from_lat_lng(latitude, longitude)
    await session.execute(
        insert(DrivingViolation),
        [
            {
                "time": datetime.now(UTC),
                "truck_id": truck_id,
                "driver_id": driver_id,
                "trip_id": trip_id,
                "violation_type": violation_type,
                "severity": severity,
                "speed_kmh": speed_kmh,
                "speed_limit_kmh": speed_limit_kmh,
                "deviation_km": deviation_km,
                "latitude": latitude,
                "longitude": longitude,
                "acknowledged": False,
                "region_code": region,
            }
        ],
    )
    await session.commit()
