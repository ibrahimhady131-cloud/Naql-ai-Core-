"""gRPC server for Fleet Service."""

from __future__ import annotations

import asyncio
import os
import uuid
from concurrent import futures

import grpc
from sqlalchemy import select

from naql.v1 import services_pb2, services_pb2_grpc
from naql_common.db.deps import init_cockroach
from naql_common.db.models.fleet import Truck

# Global DB reference
_cockroach = None


def init_db():
    """Initialize database connection for gRPC server."""
    global _cockroach
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        _cockroach = init_cockroach(db_url)
        print("[gRPC] Database connection initialized")


class FleetServiceServicer(services_pb2_grpc.FleetServiceServicer):
    """gRPC servicer implementing FleetService."""

    async def GetTruckDetails(
        self, request: services_pb2.GetTruckRequest, context: grpc.aio.ServicerContext
    ) -> services_pb2.TruckResponse:
        """Get truck details by ID via gRPC."""
        print(f"[gRPC] GetTruckDetails called for truck_id={request.truck_id}")

        if _cockroach is None:
            context.set_code(grpc.StatusCode.UNAVAILABLE)
            context.set_details("Database not initialized")
            return services_pb2.TruckResponse()

        try:
            truck_uuid = uuid.UUID(request.truck_id)
        except ValueError:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(f"Invalid truck_id format: {request.truck_id}")
            return services_pb2.TruckResponse()

        async with _cockroach.session_factory() as session:
            result = await session.execute(
                select(Truck).where(Truck.id == truck_uuid)
            )
            truck = result.scalar_one_or_none()

        if truck is None:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(f"Truck {request.truck_id} not found")
            return services_pb2.TruckResponse()

        return services_pb2.TruckResponse(
            id=str(truck.id),
            owner_id=str(truck.owner_id),
            license_plate=truck.license_plate,
            truck_type=truck.truck_type,
            load_capacity_kg=truck.load_capacity_kg,
            status=truck.status,
            region_code=truck.region_code,
            vin=truck.vin or "",
            make=truck.make or "",
            model=truck.model or "",
            has_refrigeration=truck.has_refrigeration,
        )

    async def GetTruck(
        self, request: services_pb2.GetTruckRequest, context: grpc.aio.ServicerContext
    ) -> services_pb2.TruckResponse:
        """Get truck details - delegates to GetTruckDetails."""
        return await self.GetTruckDetails(request, context)


async def serve(port: int = 50051) -> None:
    """Start the gRPC server."""
    init_db()  # Initialize DB connection
    server = grpc.aio.server(futures.ThreadPoolExecutor(max_workers=10))
    services_pb2_grpc.add_FleetServiceServicer_to_server(
        FleetServiceServicer(), server
    )
    listen_addr = f"[::]:{port}"
    server.add_insecure_port(listen_addr)
    await server.start()
    print(f"[gRPC] Fleet Service listening on {listen_addr}")
    await server.wait_for_termination()


if __name__ == "__main__":
    asyncio.run(serve())
