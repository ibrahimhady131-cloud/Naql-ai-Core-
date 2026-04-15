"""gRPC server for Identity Service."""

from __future__ import annotations

import asyncio
import os
import uuid
from concurrent import futures

import grpc
from sqlalchemy import select

from naql.v1 import services_pb2, services_pb2_grpc
from naql_common.db.deps import init_cockroach
from naql_common.db.models.identity import User

# Global DB reference
_cockroach = None


def init_db():
    """Initialize database connection for gRPC server."""
    global _cockroach
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        _cockroach = init_cockroach(db_url)
        print("[gRPC] Database connection initialized")


class IdentityServiceServicer(services_pb2_grpc.IdentityServiceServicer):
    """gRPC servicer implementing IdentityService."""

    async def GetUserDetails(
        self, request: services_pb2.GetUserRequest, context: grpc.aio.ServicerContext
    ) -> services_pb2.UserResponse:
        """Get user details by ID via gRPC."""
        print(f"[gRPC] GetUserDetails called for user_id={request.user_id}")

        if _cockroach is None:
            context.set_code(grpc.StatusCode.UNAVAILABLE)
            context.set_details("Database not initialized")
            return services_pb2.UserResponse()

        try:
            user_uuid = uuid.UUID(request.user_id)
        except ValueError:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(f"Invalid user_id format: {request.user_id}")
            return services_pb2.UserResponse()

        async with _cockroach.session_factory() as session:
            result = await session.execute(
                select(User).where(User.id == user_uuid)
            )
            user = result.scalar_one_or_none()

        if user is None:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(f"User {request.user_id} not found")
            return services_pb2.UserResponse()

        return services_pb2.UserResponse(
            id=str(user.id),
            email=user.email,
            full_name=user.full_name or "",
            role=user.role,
            phone=user.phone or "",
            region_code=user.region_code or "",
            is_active=user.is_active,
            kyc_status=user.kyc_status or "",
        )

    async def GetUser(
        self, request: services_pb2.GetUserRequest, context: grpc.aio.ServicerContext
    ) -> services_pb2.UserResponse:
        """Get user - delegates to GetUserDetails."""
        return await self.GetUserDetails(request, context)


async def serve(port: int = 50052) -> None:
    """Start the gRPC server."""
    init_db()  # Initialize DB connection
    server = grpc.aio.server(futures.ThreadPoolExecutor(max_workers=10))
    services_pb2_grpc.add_IdentityServiceServicer_to_server(
        IdentityServiceServicer(), server
    )
    listen_addr = f"[::]:{port}"
    server.add_insecure_port(listen_addr)
    await server.start()
    print(f"[gRPC] Identity Service listening on {listen_addr}")
    await server.wait_for_termination()


if __name__ == "__main__":
    asyncio.run(serve())
