"""Fleet Service API routes — fully DB-backed."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from naql_common.db.deps import CockroachSession
from naql_common.db.models.fleet import Truck, TruckMaintenance

from ..repositories import TruckRepository
from ..schemas.truck import (
    MaintenanceRequest,
    MaintenanceResponse,
    TruckListResponse,
    TruckRegisterRequest,
    TruckResponse,
    TruckStatusUpdateRequest,
)

router = APIRouter(prefix="/api/v1", tags=["fleet"])


def _truck_to_response(truck: Truck) -> TruckResponse:
    return TruckResponse(
        id=str(truck.id),
        owner_id=str(truck.owner_id),
        license_plate=truck.license_plate,
        truck_type=truck.truck_type,
        load_capacity_kg=truck.load_capacity_kg,
        region_code=truck.region_code,
        status=truck.status,
        vin=truck.vin,
        make=truck.make,
        model=truck.model,
        year=truck.year,
        has_refrigeration=truck.has_refrigeration,
        has_gps_tracker=truck.has_gps_tracker,
        created_at=truck.created_at,
    )


def _maintenance_to_response(record: TruckMaintenance) -> MaintenanceResponse:
    return MaintenanceResponse(
        id=str(record.id),
        truck_id=str(record.truck_id),
        maintenance_type=record.maintenance_type,
        description=record.description,
        cost_egp=float(record.cost_egp) if record.cost_egp is not None else None,
        performed_at=record.performed_at,
    )


@router.post("/trucks", response_model=TruckResponse, status_code=status.HTTP_201_CREATED)
async def register_truck(request: TruckRegisterRequest, session: CockroachSession) -> TruckResponse:
    """Register a new truck in the fleet."""
    repo = TruckRepository(session)
    if await repo.get_by_license_plate(request.license_plate):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="License plate already registered")

    truck = await repo.create(
        owner_id=request.owner_id,
        license_plate=request.license_plate,
        truck_type=request.truck_type,
        load_capacity_kg=request.load_capacity_kg,
        region_code=request.region_code,
        vin=request.vin,
        make=request.make,
        model=request.model,
        year=request.year,
        has_refrigeration=request.has_refrigeration,
        telemetry_device_id=request.telemetry_device_id,
    )
    return _truck_to_response(truck)


@router.get("/trucks/{truck_id}", response_model=TruckResponse)
async def get_truck(truck_id: str, session: CockroachSession) -> TruckResponse:
    """Get truck details by ID."""
    repo = TruckRepository(session)
    truck = await repo.get_by_id(truck_id)
    if truck is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Truck not found")
    return _truck_to_response(truck)


@router.patch("/trucks/{truck_id}/status", response_model=TruckResponse)
async def update_truck_status(
    truck_id: str, request: TruckStatusUpdateRequest, session: CockroachSession
) -> TruckResponse:
    """Update a truck's operational status."""
    repo = TruckRepository(session)
    truck = await repo.get_by_id(truck_id)
    if truck is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Truck not found")
    truck = await repo.update_status(truck, request.status)
    return _truck_to_response(truck)


@router.get("/trucks", response_model=TruckListResponse)
async def list_trucks(
    session: CockroachSession,
    page: int = 1,
    page_size: int = 20,
    truck_type: str | None = None,
    status_filter: str | None = None,
    region_code: str | None = None,
) -> TruckListResponse:
    """List trucks with pagination and filtering."""
    repo = TruckRepository(session)
    offset = (page - 1) * page_size
    trucks = await repo.list_trucks(
        truck_type=truck_type, status=status_filter, region_code=region_code,
        offset=offset, limit=page_size,
    )
    total = await repo.count_trucks(
        truck_type=truck_type, status=status_filter, region_code=region_code
    )
    return TruckListResponse(
        trucks=[_truck_to_response(t) for t in trucks],
        total=total, page=page, page_size=page_size,
        has_next=(offset + page_size) < total,
    )


@router.get("/trucks/owner/{owner_id}", response_model=TruckListResponse)
async def get_trucks_by_owner(
    owner_id: str,
    session: CockroachSession,
    page: int = 1,
    page_size: int = 20,
) -> TruckListResponse:
    """Get all trucks owned by a specific user."""
    repo = TruckRepository(session)
    offset = (page - 1) * page_size
    trucks = await repo.list_trucks(owner_id=owner_id, offset=offset, limit=page_size)
    total = await repo.count_trucks(owner_id=owner_id)
    return TruckListResponse(
        trucks=[_truck_to_response(t) for t in trucks],
        total=total, page=page, page_size=page_size,
        has_next=(offset + page_size) < total,
    )


@router.post("/trucks/{truck_id}/maintenance", response_model=MaintenanceResponse, status_code=status.HTTP_201_CREATED)
async def add_maintenance(
    truck_id: str, request: MaintenanceRequest, session: CockroachSession
) -> MaintenanceResponse:
    """Add a maintenance record for a truck."""
    repo = TruckRepository(session)
    if await repo.get_by_id(truck_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Truck not found")
    record = await repo.add_maintenance(
        truck_id=truck_id,
        maintenance_type=request.maintenance_type,
        performed_at=request.performed_at,
        description=request.description,
        cost_egp=request.cost_egp,
        odometer_km=request.odometer_km,
        next_due_at=request.next_due_at,
        performed_by=request.performed_by,
    )
    return _maintenance_to_response(record)
