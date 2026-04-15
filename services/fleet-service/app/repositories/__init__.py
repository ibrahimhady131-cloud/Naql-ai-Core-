"""Fleet Service repository — database-backed truck and maintenance operations."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from naql_common.db.models.fleet import Truck, TruckMaintenance


class TruckRepository:
    """CRUD operations for the trucks table via SQLAlchemy."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, truck_id: str) -> Truck | None:
        result = await self._session.execute(
            select(Truck).where(Truck.id == uuid.UUID(truck_id), Truck.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def get_by_license_plate(self, plate: str) -> Truck | None:
        result = await self._session.execute(
            select(Truck).where(Truck.license_plate == plate, Truck.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        owner_id: str,
        license_plate: str,
        truck_type: str,
        load_capacity_kg: int,
        region_code: str,
        vin: str | None = None,
        make: str | None = None,
        model: str | None = None,
        year: int | None = None,
        has_refrigeration: bool = False,
        has_gps_tracker: bool = True,
        telemetry_device_id: str | None = None,
        insurance_expiry: datetime | None = None,
        license_expiry: datetime | None = None,
    ) -> Truck:
        truck = Truck(
            id=uuid.uuid4(),
            owner_id=uuid.UUID(owner_id),
            license_plate=license_plate,
            truck_type=truck_type,
            load_capacity_kg=load_capacity_kg,
            region_code=region_code,
            vin=vin,
            make=make,
            model=model,
            year=year,
            has_refrigeration=has_refrigeration,
            has_gps_tracker=has_gps_tracker,
            telemetry_device_id=telemetry_device_id,
            insurance_expiry=insurance_expiry,
            license_expiry=license_expiry,
            status="offline",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        self._session.add(truck)
        await self._session.flush()
        return truck

    async def update_status(self, truck: Truck, status: str) -> Truck:
        truck.status = status
        truck.updated_at = datetime.now(UTC)
        await self._session.flush()
        return truck

    async def list_trucks(
        self,
        *,
        truck_type: str | None = None,
        status: str | None = None,
        region_code: str | None = None,
        owner_id: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> list[Truck]:
        stmt = select(Truck).where(Truck.deleted_at.is_(None))
        if truck_type:
            stmt = stmt.where(Truck.truck_type == truck_type)
        if status:
            stmt = stmt.where(Truck.status == status)
        if region_code:
            stmt = stmt.where(Truck.region_code == region_code)
        if owner_id:
            stmt = stmt.where(Truck.owner_id == uuid.UUID(owner_id))
        stmt = stmt.offset(offset).limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def count_trucks(
        self,
        *,
        truck_type: str | None = None,
        status: str | None = None,
        region_code: str | None = None,
        owner_id: str | None = None,
    ) -> int:
        from sqlalchemy import func
        stmt = select(func.count(Truck.id)).where(Truck.deleted_at.is_(None))
        if truck_type:
            stmt = stmt.where(Truck.truck_type == truck_type)
        if status:
            stmt = stmt.where(Truck.status == status)
        if region_code:
            stmt = stmt.where(Truck.region_code == region_code)
        if owner_id:
            stmt = stmt.where(Truck.owner_id == uuid.UUID(owner_id))
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def add_maintenance(
        self,
        *,
        truck_id: str,
        maintenance_type: str,
        performed_at: datetime,
        description: str | None = None,
        cost_egp: float | None = None,
        odometer_km: int | None = None,
        next_due_at: datetime | None = None,
        performed_by: str | None = None,
    ) -> TruckMaintenance:
        record = TruckMaintenance(
            id=uuid.uuid4(),
            truck_id=uuid.UUID(truck_id),
            maintenance_type=maintenance_type,
            performed_at=performed_at,
            description=description,
            cost_egp=cost_egp,
            odometer_km=odometer_km,
            next_due_at=next_due_at,
            performed_by=performed_by,
        )
        self._session.add(record)
        await self._session.flush()
        return record
