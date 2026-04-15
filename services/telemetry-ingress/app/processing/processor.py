"""MQTT message processor for truck telemetry data.

Handles incoming MQTT messages from EMQX broker:
- GPS position updates
- OBD-II sensor data
- Driver alerts

Implements batching and buffering for efficient TimescaleDB writes.
Maintains real-time truck positions in Redis GEO index.
"""

from __future__ import annotations

import json
from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from naql_common.geo import Coordinate, find_hub


@dataclass
class PositionMessage:
    """Parsed GPS position update from MQTT."""

    truck_id: str
    driver_id: str | None
    trip_id: str | None
    latitude: float
    longitude: float
    altitude_m: float | None
    speed_kmh: float
    heading: float | None
    signal_strength: int | None
    connection_type: str | None
    ignition_on: bool
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class TelemetryMessage:
    """Parsed OBD-II / sensor telemetry from MQTT."""

    truck_id: str
    engine_rpm: int | None
    engine_temp_c: float | None
    fuel_level_pct: float | None
    fuel_rate_lph: float | None
    odometer_km: float | None
    battery_voltage: float | None
    cargo_temp_c: float | None
    harsh_braking: bool
    harsh_acceleration: bool
    sharp_turn: bool
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


class MessageProcessor:
    """Processes incoming MQTT messages and buffers for batch writes.

    Implements the "Speed of Light" data layer:
    1. Parse MQTT message
    2. Update Redis GEO index (real-time)
    3. Buffer for TimescaleDB batch insert
    4. Check geofence violations
    5. Emit events to NATS if anomalies detected
    """

    def __init__(self, batch_size: int = 100) -> None:
        self._batch_size = batch_size
        self._position_buffer: deque[PositionMessage] = deque()
        self._telemetry_buffer: deque[TelemetryMessage] = deque()
        self._geofence_states: dict[str, str | None] = {}  # truck_id → current_hub

    def parse_position(self, topic: str, payload: bytes) -> PositionMessage:
        """Parse a position MQTT message."""
        data = json.loads(payload.decode("utf-8"))

        # Extract truck_id from topic: naql/truck/{truck_id}/position
        parts = topic.split("/")
        truck_id = parts[2] if len(parts) >= 4 else data.get("truck_id", "unknown")

        return PositionMessage(
            truck_id=truck_id,
            driver_id=data.get("driver_id"),
            trip_id=data.get("trip_id"),
            latitude=data["latitude"],
            longitude=data["longitude"],
            altitude_m=data.get("altitude_m"),
            speed_kmh=data.get("speed_kmh", 0.0),
            heading=data.get("heading"),
            signal_strength=data.get("signal_strength"),
            connection_type=data.get("connection_type"),
            ignition_on=data.get("ignition_on", True),
        )

    def parse_telemetry(self, topic: str, payload: bytes) -> TelemetryMessage:
        """Parse a telemetry MQTT message."""
        data = json.loads(payload.decode("utf-8"))

        parts = topic.split("/")
        truck_id = parts[2] if len(parts) >= 4 else data.get("truck_id", "unknown")

        return TelemetryMessage(
            truck_id=truck_id,
            engine_rpm=data.get("engine_rpm"),
            engine_temp_c=data.get("engine_temp_c"),
            fuel_level_pct=data.get("fuel_level_pct"),
            fuel_rate_lph=data.get("fuel_rate_lph"),
            odometer_km=data.get("odometer_km"),
            battery_voltage=data.get("battery_voltage"),
            cargo_temp_c=data.get("cargo_temp_c"),
            harsh_braking=data.get("harsh_braking", False),
            harsh_acceleration=data.get("harsh_acceleration", False),
            sharp_turn=data.get("sharp_turn", False),
        )

    def process_position(self, msg: PositionMessage) -> list[dict[str, Any]]:
        """Process a position update. Returns any events to emit."""
        events: list[dict[str, Any]] = []

        # Buffer for batch write
        self._position_buffer.append(msg)

        # Check geofence
        coord = Coordinate(msg.latitude, msg.longitude)
        current_hub = find_hub(coord)
        previous_hub = self._geofence_states.get(msg.truck_id)

        if current_hub != previous_hub:
            if previous_hub is not None:
                events.append(
                    {
                        "type": "geofence_exited",
                        "truck_id": msg.truck_id,
                        "hub": previous_hub,
                        "latitude": msg.latitude,
                        "longitude": msg.longitude,
                    }
                )
            if current_hub is not None:
                events.append(
                    {
                        "type": "geofence_entered",
                        "truck_id": msg.truck_id,
                        "hub": current_hub,
                        "latitude": msg.latitude,
                        "longitude": msg.longitude,
                    }
                )
            self._geofence_states[msg.truck_id] = current_hub

        # Check speed violation (120 km/h limit on Egyptian highways)
        if msg.speed_kmh > 120:
            events.append(
                {
                    "type": "speed_violation",
                    "truck_id": msg.truck_id,
                    "speed_kmh": msg.speed_kmh,
                    "limit_kmh": 120,
                    "latitude": msg.latitude,
                    "longitude": msg.longitude,
                }
            )

        return events

    def process_telemetry(self, msg: TelemetryMessage) -> list[dict[str, Any]]:
        """Process a telemetry update. Returns any events to emit."""
        events: list[dict[str, Any]] = []

        # Buffer for batch write
        self._telemetry_buffer.append(msg)

        # Check for engine overheating
        if msg.engine_temp_c is not None and msg.engine_temp_c > 110:
            events.append(
                {
                    "type": "engine_overheat",
                    "truck_id": msg.truck_id,
                    "temperature_c": msg.engine_temp_c,
                    "severity": "critical",
                }
            )

        # Check for low fuel
        if msg.fuel_level_pct is not None and msg.fuel_level_pct < 10:
            events.append(
                {
                    "type": "low_fuel",
                    "truck_id": msg.truck_id,
                    "fuel_level_pct": msg.fuel_level_pct,
                    "severity": "warning",
                }
            )

        # Check for harsh driving events
        if msg.harsh_braking or msg.harsh_acceleration or msg.sharp_turn:
            events.append(
                {
                    "type": "harsh_driving",
                    "truck_id": msg.truck_id,
                    "harsh_braking": msg.harsh_braking,
                    "harsh_acceleration": msg.harsh_acceleration,
                    "sharp_turn": msg.sharp_turn,
                    "severity": "info",
                }
            )

        return events

    def flush_position_buffer(self) -> list[PositionMessage]:
        """Flush position buffer for batch insert."""
        batch = list(self._position_buffer)
        self._position_buffer.clear()
        return batch

    def flush_telemetry_buffer(self) -> list[TelemetryMessage]:
        """Flush telemetry buffer for batch insert."""
        batch = list(self._telemetry_buffer)
        self._telemetry_buffer.clear()
        return batch

    @property
    def position_buffer_size(self) -> int:
        return len(self._position_buffer)

    @property
    def telemetry_buffer_size(self) -> int:
        return len(self._telemetry_buffer)
