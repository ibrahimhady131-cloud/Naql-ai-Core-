"""Pydantic schemas for Fleet Service API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class TruckRegisterRequest(BaseModel):
    """Request schema for truck registration."""

    owner_id: str
    license_plate: str = Field(..., max_length=20)
    truck_type: str = Field(
        ..., pattern=r"^(quarter|half|full|jumbo|trailer|refrigerated|tanker|flatbed)$"
    )
    load_capacity_kg: int = Field(..., gt=0, le=50000)
    vin: str | None = Field(None, max_length=17)
    make: str | None = Field(None, max_length=50)
    model: str | None = Field(None, max_length=50)
    year: int | None = Field(None, ge=1990, le=2030)
    has_refrigeration: bool = False
    region_code: str = Field(..., pattern=r"^EG-[A-Z]{3}$")
    telemetry_device_id: str | None = None


class TruckResponse(BaseModel):
    """Response schema for truck data."""

    id: str
    owner_id: str
    license_plate: str
    truck_type: str
    load_capacity_kg: int
    status: str
    region_code: str
    vin: str | None = None
    make: str | None = None
    model: str | None = None
    year: int | None = None
    has_refrigeration: bool
    has_gps_tracker: bool = True
    created_at: datetime

    model_config = {"from_attributes": True}


class TruckStatusUpdateRequest(BaseModel):
    """Request schema for updating truck status."""

    status: str = Field(
        ...,
        pattern=r"^(available|en_route|loading|unloading|maintenance|offline)$",
    )


class TruckListResponse(BaseModel):
    """Paginated truck list response."""

    trucks: list[TruckResponse]
    total: int
    page: int
    page_size: int
    has_next: bool


class MaintenanceRequest(BaseModel):
    """Request schema for adding maintenance record."""

    maintenance_type: str = Field(..., pattern=r"^(scheduled|emergency|inspection)$")
    description: str = Field(..., max_length=1000)
    cost_egp: float = Field(..., ge=0)
    odometer_km: int = Field(..., ge=0)
    performed_at: datetime
    next_due_at: datetime | None = None
    performed_by: str | None = None


class MaintenanceResponse(BaseModel):
    """Response schema for maintenance record."""

    id: str
    truck_id: str
    maintenance_type: str
    description: str | None
    cost_egp: float | None
    performed_at: datetime

    model_config = {"from_attributes": True}
