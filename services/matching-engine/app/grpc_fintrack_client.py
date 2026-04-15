"""gRPC client for FinTrack Service communication."""

from __future__ import annotations

import grpc
from naql.v1 import services_pb2, services_pb2_grpc


class FinTrackClient:
    """Client for calling FinTrack Service via gRPC."""

    def __init__(self, host: str = "127.0.0.1", port: int = 50054):
        self.channel = grpc.aio.insecure_channel(f"{host}:{port}")
        self.stub = services_pb2_grpc.FinTrackServiceStub(self.channel)

    async def create_invoice(
        self, shipment_id: str, shipper_id: str, amount: float, currency: str = "EGP"
    ) -> services_pb2.InvoiceResponse | None:
        """Create invoice via gRPC."""
        print(f"[gRPC Client] Calling FinTrack Service CreateInvoice for shipment_id={shipment_id}")
        try:
            response = await self.stub.CreateInvoice(
                services_pb2.InvoiceRequest(
                    shipment_id=shipment_id,
                    shipper_id=shipper_id,
                    amount=amount,
                    currency=currency,
                ),
                timeout=5.0,
            )
            print(f"[gRPC Client] Invoice created: {response.invoice_id}, status={response.status}")
            return response
        except grpc.RpcError as e:
            print(f"[gRPC Client] Error: {e.code()} - {e.details()}")
            return None

    async def close(self) -> None:
        """Close the gRPC channel."""
        await self.channel.close()


_fintrack_client: FinTrackClient | None = None


def get_fintrack_client() -> FinTrackClient:
    """Get or create the FinTrack gRPC client singleton."""
    global _fintrack_client
    if _fintrack_client is None:
        _fintrack_client = FinTrackClient()
    return _fintrack_client


async def close_fintrack_client() -> None:
    """Close the FinTrack gRPC client."""
    global _fintrack_client
    if _fintrack_client is not None:
        await _fintrack_client.close()
        _fintrack_client = None
