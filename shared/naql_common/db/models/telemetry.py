"""SQLAlchemy ORM models for Telemetry (TimescaleDB hypertables)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from naql_common.db.base import Base


class TruckPosition(Base):
    """GPS position records — stored in TimescaleDB hypertable (7-day chunks)."""

    __tablename__ = "truck_positions"

    # Composite primary key: (time, truck_id)
    time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), primary_key=True, nullable=False
    )
    truck_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, nullable=False
    )
    driver_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    trip_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )

    # Position
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    altitude_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    accuracy_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    h3_index: Mapped[str] = mapped_column(Text, nullable=False)

    # Motion
    speed_kmh: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    heading: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Network
    signal_strength: Mapped[int | None] = mapped_column(Integer, nullable=True)
    connection_type: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Status
    ignition_on: Mapped[bool] = mapped_column(Boolean, default=True, nullable=True)
    region_code: Mapped[str] = mapped_column(Text, nullable=False)


class TruckTelemetry(Base):
    """OBD-II / IoT sensor telemetry — TimescaleDB hypertable."""

    __tablename__ = "truck_telemetry"

    time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), primary_key=True, nullable=False
    )
    truck_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, nullable=False
    )

    # Engine
    engine_rpm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    engine_temp_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    fuel_level_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    fuel_rate_lph: Mapped[float | None] = mapped_column(Float, nullable=True)
    odometer_km: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Diagnostics
    battery_voltage: Mapped[float | None] = mapped_column(Float, nullable=True)
    dtc_codes: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    check_engine: Mapped[bool] = mapped_column(Boolean, default=False, nullable=True)

    # Environment
    cargo_temp_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    ambient_temp_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    humidity_pct: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Driving behavior
    harsh_braking: Mapped[bool] = mapped_column(Boolean, default=False, nullable=True)
    harsh_acceleration: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=True
    )
    sharp_turn: Mapped[bool] = mapped_column(Boolean, default=False, nullable=True)

    region_code: Mapped[str] = mapped_column(Text, nullable=False)


class GeofenceEvent(Base):
    """Geofence enter/exit events — TimescaleDB hypertable."""

    __tablename__ = "geofence_events"

    time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), primary_key=True, nullable=False
    )
    truck_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, nullable=False
    )
    trip_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )

    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    geofence_name: Mapped[str] = mapped_column(Text, nullable=False)
    geofence_type: Mapped[str] = mapped_column(Text, nullable=False)

    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)

    dwell_time_sec: Mapped[int | None] = mapped_column(Integer, nullable=True)
    region_code: Mapped[str] = mapped_column(Text, nullable=False)


class DrivingViolation(Base):
    """Speed & route violations — TimescaleDB hypertable."""

    __tablename__ = "driving_violations"

    time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), primary_key=True, nullable=False
    )
    truck_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, nullable=False
    )
    driver_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    trip_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )

    violation_type: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(Text, nullable=False)

    speed_kmh: Mapped[float | None] = mapped_column(Float, nullable=True)
    speed_limit_kmh: Mapped[float | None] = mapped_column(Float, nullable=True)
    deviation_km: Mapped[float | None] = mapped_column(Float, nullable=True)

    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)

    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False, nullable=True)
    region_code: Mapped[str] = mapped_column(Text, nullable=False)
