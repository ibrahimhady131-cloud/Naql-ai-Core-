"""gRPC client for Fleet Service communication."""

from __future__ import annotations

import grpc
from naql.v1 import services_pb2, services_pb2_grpc


class FleetClient:
    """Client for calling Fleet Service via gRPC."""

    def __init__(self, host: str = "127.0.0.1", port: int = 50051):
        self.channel = grpc.aio.insecure_channel(f"{host}:{port}")
        self.stub = services_pb2_grpc.FleetServiceStub(self.channel)

    async def get_truck_details(self, truck_id: str) -> services_pb2.TruckResponse | None:
        """Get truck details from Fleet Service via gRPC."""
        print(f"[gRPC Client] Calling Fleet Service GetTruckDetails for truck_id={truck_id}")
        try:
            response = await self.stub.GetTruckDetails(
                services_pb2.GetTruckRequest(truck_id=truck_id),
                timeout=5.0,
            )
            print(f"[gRPC Client] Received response: truck_type={response.truck_type}, load_capacity_kg={response.load_capacity_kg}")
            return response
        except grpc.RpcError as e:
            print(f"[gRPC Client] Error: {e.code()} - {e.details()}")
            return None

    async def close(self) -> None:
        """Close the gRPC channel."""
        await self.channel.close()


_fleet_client: FleetClient | None = None


def get_fleet_client() -> FleetClient:
    """Get or create the Fleet gRPC client singleton."""
    global _fleet_client
    if _fleet_client is None:
        _fleet_client = FleetClient()
    return _fleet_client


async def close_fleet_client() -> None:
    """Close the Fleet gRPC client."""
    global _fleet_client
    if _fleet_client is not None:
        await _fleet_client.close()
        _fleet_client = None
