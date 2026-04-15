"""gRPC client for Identity Service communication."""

from __future__ import annotations

import grpc
from naql.v1 import services_pb2, services_pb2_grpc


class IdentityClient:
    """Client for calling Identity Service via gRPC."""

    def __init__(self, host: str = "127.0.0.1", port: int = 50052):
        self.channel = grpc.aio.insecure_channel(f"{host}:{port}")
        self.stub = services_pb2_grpc.IdentityServiceStub(self.channel)

    async def get_user_details(self, user_id: str) -> services_pb2.UserResponse | None:
        """Get user details from Identity Service via gRPC."""
        print(f"[gRPC Client] Calling Identity Service GetUserDetails for user_id={user_id}")
        try:
            response = await self.stub.GetUserDetails(
                services_pb2.GetUserRequest(user_id=user_id),
                timeout=5.0,
            )
            print(f"[gRPC Client] Received response: role={response.role}, is_active={response.is_active}")
            return response
        except grpc.RpcError as e:
            print(f"[gRPC Client] Error: {e.code()} - {e.details()}")
            return None

    async def verify_shipper(self, user_id: str) -> tuple[bool, str]:
        """Verify if user exists and has Shipper role."""
        user = await self.get_user_details(user_id)
        if user is None:
            return False, "User not found or Identity Service unavailable"
        if not user.is_active:
            return False, f"User {user_id} is not active"
        if user.role.lower() not in ("shipper", "client_enterprise", "client_individual"):
            return False, f"User {user_id} is not a Shipper (role: {user.role})"
        return True, "Shipper verified"

    async def close(self) -> None:
        """Close the gRPC channel."""
        await self.channel.close()


_identity_client: IdentityClient | None = None


def get_identity_client() -> IdentityClient:
    """Get or create the Identity gRPC client singleton."""
    global _identity_client
    if _identity_client is None:
        _identity_client = IdentityClient()
    return _identity_client


async def close_identity_client() -> None:
    """Close the Identity gRPC client."""
    global _identity_client
    if _identity_client is not None:
        await _identity_client.close()
        _identity_client = None
