"""SQLAlchemy ORM models for Shipments, Trips, and Matching (CockroachDB)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from naql_common.db.base import Base, RegionalMixin, TimestampMixin


class Shipment(Base, TimestampMixin, RegionalMixin):
    """Shipments / Orders table."""

    __tablename__ = "shipments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    reference_number: Mapped[str] = mapped_column(
        String(20), unique=True, nullable=False
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )

    # Origin
    origin_address: Mapped[str] = mapped_column(String(500), nullable=False)
    origin_lat: Mapped[float] = mapped_column(Numeric(10, 7), nullable=False)
    origin_lng: Mapped[float] = mapped_column(Numeric(10, 7), nullable=False)
    origin_h3_index: Mapped[str] = mapped_column(String(15), nullable=False, index=True)
    origin_hub: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Destination
    dest_address: Mapped[str] = mapped_column(String(500), nullable=False)
    dest_lat: Mapped[float] = mapped_column(Numeric(10, 7), nullable=False)
    dest_lng: Mapped[float] = mapped_column(Numeric(10, 7), nullable=False)
    dest_h3_index: Mapped[str] = mapped_column(String(15), nullable=False, index=True)
    dest_hub: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Cargo
    commodity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    weight_kg: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    volume_cbm: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)
    requires_refrigeration: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    temperature_min_c: Mapped[float | None] = mapped_column(
        Numeric(4, 1), nullable=True
    )
    temperature_max_c: Mapped[float | None] = mapped_column(
        Numeric(4, 1), nullable=True
    )
    is_hazardous: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    hazmat_class: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # Requirements
    required_truck_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    containers_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    pickup_window_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    pickup_window_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    delivery_deadline: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Pricing
    quoted_price_egp: Mapped[float | None] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    fuel_cost_egp: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    toll_cost_egp: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    service_fee_egp: Mapped[float | None] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    insurance_fee_egp: Mapped[float | None] = mapped_column(
        Numeric(10, 2), nullable=True
    )

    # State
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default="draft", index=True
    )
    status_history: Mapped[dict] = mapped_column(JSONB, nullable=False, default=[])

    # Metadata
    distance_km: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)
    estimated_duration_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(String(2000), nullable=True)


class ShipmentAuditLog(Base):
    """Versioned audit trail for shipment state changes."""

    __tablename__ = "shipment_audit_log"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    shipment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    previous_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    new_status: Mapped[str] = mapped_column(String(30), nullable=False)
    changed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    change_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    audit_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Trip(Base, TimestampMixin, RegionalMixin):
    """Active transport trips."""

    __tablename__ = "trips"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    shipment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    driver_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    truck_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )

    # Route
    planned_route_polyline: Mapped[str | None] = mapped_column(Text, nullable=True)
    actual_route_polyline: Mapped[str | None] = mapped_column(Text, nullable=True)
    planned_distance_km: Mapped[float | None] = mapped_column(
        Numeric(8, 2), nullable=True
    )
    actual_distance_km: Mapped[float | None] = mapped_column(
        Numeric(8, 2), nullable=True
    )

    # Timing
    accepted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    pickup_arrived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    picked_up_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    delivered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    estimated_arrival: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Real-time position
    current_lat: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)
    current_lng: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)
    current_speed_kmh: Mapped[float | None] = mapped_column(
        Numeric(5, 1), nullable=True
    )
    current_heading: Mapped[float | None] = mapped_column(
        Numeric(5, 2), nullable=True
    )

    # Fuel & tolls
    fuel_consumed_liters: Mapped[float | None] = mapped_column(
        Numeric(8, 2), nullable=True
    )
    toll_checkpoints: Mapped[dict] = mapped_column(JSONB, nullable=False, default=[])

    # Ratings
    client_rating: Mapped[float | None] = mapped_column(Numeric(2, 1), nullable=True)
    driver_rating: Mapped[float | None] = mapped_column(Numeric(2, 1), nullable=True)

    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="assigned", index=True
    )


class MatchHistory(Base):
    """Match history for analytics and learning."""

    __tablename__ = "match_history"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    shipment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    driver_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    score: Mapped[float] = mapped_column(Numeric(5, 3), nullable=False)
    factors: Mapped[dict] = mapped_column(JSONB, nullable=False)
    offered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    responded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    response: Mapped[str | None] = mapped_column(String(20), nullable=True)


class DriverPreferences(Base):
    """Driver matching preferences."""

    __tablename__ = "driver_preferences"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    driver_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), unique=True, nullable=False
    )
    preferred_routes: Mapped[dict] = mapped_column(JSONB, nullable=False, default=[])
    max_distance_km: Mapped[int] = mapped_column(Integer, nullable=False, default=500)
    min_price_egp: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    preferred_cargo: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, default=[]
    )
    blacklisted_clients: Mapped[list[str]] = mapped_column(
        ARRAY(UUID(as_uuid=True)), nullable=False, default=[]
    )
    auto_accept: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    working_hours: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(),
        nullable=False,
    )
