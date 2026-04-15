"""SQLAlchemy models for Fleet Service."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from naql_common.db.base import Base, SoftDeleteMixin, TimestampMixin


class Truck(Base, TimestampMixin, SoftDeleteMixin):
    """Truck entity model."""

    __tablename__ = "trucks"

    id: Mapped[str] = mapped_column(UUID, primary_key=True, server_default=func.gen_random_uuid())
    owner_id: Mapped[str] = mapped_column(UUID, nullable=False, index=True)
    vin: Mapped[str | None] = mapped_column(String(17), unique=True)
    license_plate: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    truck_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    make: Mapped[str | None] = mapped_column(String(50))
    model: Mapped[str | None] = mapped_column(String(50))
    year: Mapped[int | None] = mapped_column(Integer)
    load_capacity_kg: Mapped[int] = mapped_column(Integer, nullable=False)
    has_refrigeration: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    has_gps_tracker: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    telemetry_device_id: Mapped[str | None] = mapped_column(String(100))
    insurance_expiry: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    license_expiry: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="offline", index=True)
    region_code: Mapped[str] = mapped_column(String(10), nullable=False, index=True)


class TruckMaintenance(Base):
    """Truck maintenance record model."""

    __tablename__ = "truck_maintenance"

    id: Mapped[str] = mapped_column(UUID, primary_key=True, server_default=func.gen_random_uuid())
    truck_id: Mapped[str] = mapped_column(UUID, nullable=False, index=True)
    maintenance_type: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000))
    cost_egp: Mapped[float | None] = mapped_column(Numeric(12, 2))
    odometer_km: Mapped[int | None] = mapped_column(Integer)
    performed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    next_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    performed_by: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
