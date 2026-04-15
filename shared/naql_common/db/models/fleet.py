"""SQLAlchemy ORM models for Fleet Service (CockroachDB)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from naql_common.db.base import Base, RegionalMixin, SoftDeleteMixin, TimestampMixin


class Truck(Base, TimestampMixin, SoftDeleteMixin, RegionalMixin):
    """Trucks table — fleet lifecycle management."""

    __tablename__ = "trucks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    vin: Mapped[str | None] = mapped_column(String(17), unique=True, nullable=True)
    license_plate: Mapped[str] = mapped_column(
        String(20), unique=True, nullable=False
    )
    truck_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    make: Mapped[str | None] = mapped_column(String(50), nullable=True)
    model: Mapped[str | None] = mapped_column(String(50), nullable=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    load_capacity_kg: Mapped[int] = mapped_column(Integer, nullable=False)
    has_refrigeration: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    has_gps_tracker: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    telemetry_device_id: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )
    insurance_expiry: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    license_expiry: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="offline", index=True
    )

    # Relationships
    maintenance_records: Mapped[list[TruckMaintenance]] = relationship(
        back_populates="truck", lazy="selectin"
    )


class TruckMaintenance(Base):
    """Truck maintenance history."""

    __tablename__ = "truck_maintenance"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    truck_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("trucks.id"), nullable=False, index=True
    )
    maintenance_type: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    cost_egp: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    odometer_km: Mapped[int | None] = mapped_column(Integer, nullable=True)
    performed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    next_due_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    performed_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    truck: Mapped[Truck] = relationship(back_populates="maintenance_records")
