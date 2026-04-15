"""gRPC server for FinTrack Service."""

from __future__ import annotations

import asyncio
import os
import uuid
from concurrent import futures

import grpc
from sqlalchemy import select

from naql.v1 import services_pb2, services_pb2_grpc
from naql_common.db.deps import init_cockroach
from naql_common.db.models.fintrack import Invoice, LedgerEntry

# Global DB reference
_cockroach = None


def init_db():
    """Initialize database connection for gRPC server."""
    global _cockroach
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        _cockroach = init_cockroach(db_url)
        print("[gRPC] Database connection initialized")


class FinTrackServiceServicer(services_pb2_grpc.FinTrackServiceServicer):
    """gRPC servicer implementing FinTrackService."""

    async def CreateInvoice(
        self, request: services_pb2.InvoiceRequest, context: grpc.aio.ServicerContext
    ) -> services_pb2.InvoiceResponse:
        """Create invoice via gRPC."""
        print(f"[gRPC] CreateInvoice called for shipment_id={request.shipment_id}, amount={request.amount} {request.currency}")

        if _cockroach is None:
            context.set_code(grpc.StatusCode.UNAVAILABLE)
            context.set_details("Database not initialized")
            return services_pb2.InvoiceResponse()

        try:
            shipment_uuid = uuid.UUID(request.shipment_id)
            shipper_uuid = uuid.UUID(request.shipper_id)
        except ValueError as e:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(f"Invalid UUID format: {e}")
            return services_pb2.InvoiceResponse()

        async with _cockroach.session_factory() as session:
            # Create invoice
            invoice = Invoice(
                id=uuid.uuid4(),
                shipment_id=shipment_uuid,
                total_amount_egp=request.amount,
                status="pending",
            )
            session.add(invoice)

            # Create initial ledger entry (Credit) - use shipper_id as account_id
            ledger_entry = LedgerEntry(
                id=uuid.uuid4(),
                account_id=shipper_uuid,
                transaction_type="credit",
                amount_egp=request.amount,
                description=f"Invoice created for shipment {request.shipment_id}",
            )
            session.add(ledger_entry)

            await session.commit()
            await session.refresh(invoice)

            print(f"[gRPC] Invoice created: {invoice.id}")

            return services_pb2.InvoiceResponse(
                invoice_id=str(invoice.id),
                shipment_id=request.shipment_id,
                amount=request.amount,
                currency=request.currency,
                status=invoice.status,
            )


async def serve(port: int = 50054) -> None:
    """Start the gRPC server."""
    init_db()  # Initialize DB connection
    server = grpc.aio.server(futures.ThreadPoolExecutor(max_workers=10))
    services_pb2_grpc.add_FinTrackServiceServicer_to_server(
        FinTrackServiceServicer(), server
    )
    listen_addr = f"[::]:{port}"
    server.add_insecure_port(listen_addr)
    await server.start()
    print(f"[gRPC] FinTrack Service listening on {listen_addr}")
    await server.wait_for_termination()


if __name__ == "__main__":
    asyncio.run(serve())
