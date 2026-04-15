"""FinTrack Service API routes."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from naql_common.utils import TruckType

from naql_common.db.deps import CockroachSession
from naql_common.db.models.fintrack import Invoice

from ..core.pricing import calculate_quote
from ..schemas.finance import (
    BalanceResponse,
    EscrowCreateRequest,
    EscrowReleaseRequest,
    EscrowResponse,
    InvoiceCreateRequest,
    InvoiceResponse,
    PaymentRequest,
    PaymentResponse,
    QuoteRequest,
    QuoteResponse,
    TransactionHistoryResponse,
    TransactionRecord,
)

router = APIRouter(prefix="/api/v1", tags=["fintrack"])

# In-memory stores for demo
_quotes_db: dict[str, dict] = {}
_escrows_db: dict[str, dict] = {}
_transactions_db: dict[str, dict] = {}
_balances_db: dict[str, dict] = {}


@router.post("/invoices", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
async def create_invoice(request: InvoiceCreateRequest, session: CockroachSession) -> InvoiceResponse:
    """Create an invoice for a shipment."""
    invoice = Invoice(
        shipment_id=uuid.UUID(request.shipment_id),
        total_amount_egp=request.total_amount_egp,
        status="unpaid",
    )
    session.add(invoice)
    await session.commit()
    await session.refresh(invoice)

    return InvoiceResponse(
        id=str(invoice.id),
        shipment_id=str(invoice.shipment_id),
        total_amount_egp=float(invoice.total_amount_egp),
        status=invoice.status,
        created_at=invoice.created_at,
    )


@router.get("/invoices/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(invoice_id: str, session: CockroachSession) -> InvoiceResponse:
    """Get an invoice by ID."""
    result = await session.execute(select(Invoice).where(Invoice.id == uuid.UUID(invoice_id)))
    invoice = result.scalar_one_or_none()
    if invoice is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")

    return InvoiceResponse(
        id=str(invoice.id),
        shipment_id=str(invoice.shipment_id),
        total_amount_egp=float(invoice.total_amount_egp),
        status=invoice.status,
        created_at=invoice.created_at,
    )


def _get_or_create_balance(user_id: str) -> dict:
    """Get or create a user's balance record."""
    if user_id not in _balances_db:
        _balances_db[user_id] = {
            "user_id": user_id,
            "available_egp": 0.0,
            "held_egp": 0.0,
            "total_egp": 0.0,
        }
    return _balances_db[user_id]


@router.post("/quotes", response_model=QuoteResponse)
async def create_quote(request: QuoteRequest) -> QuoteResponse:
    """Generate a price quote for a shipment."""
    truck_type = TruckType(request.truck_type)

    breakdown = calculate_quote(
        distance_km=request.distance_km,
        truck_type=truck_type,
        weight_kg=request.weight_kg,
        origin_region=request.origin_region,
        dest_region=request.dest_region,
        requires_refrigeration=request.requires_refrigeration,
    )

    quote_id = f"QUO-{uuid.uuid4().hex[:8].upper()}"
    valid_until = datetime.now(UTC) + timedelta(hours=24)

    _quotes_db[quote_id] = {
        "quote_id": quote_id,
        **request.model_dump(),
        "breakdown": breakdown,
        "valid_until": valid_until,
    }

    return QuoteResponse(
        quote_id=quote_id,
        total_egp=breakdown.total_egp,
        fuel_cost_egp=breakdown.fuel_cost_egp,
        toll_cost_egp=breakdown.toll_cost_egp,
        service_fee_egp=breakdown.service_fee_egp,
        insurance_fee_egp=breakdown.insurance_fee_egp,
        valid_until=valid_until,
    )


@router.post("/escrow", response_model=EscrowResponse, status_code=status.HTTP_201_CREATED)
async def create_escrow(request: EscrowCreateRequest) -> EscrowResponse:
    """Create an escrow hold for a shipment payment."""
    escrow_id = f"ESC-{uuid.uuid4().hex[:8].upper()}"

    # Hold funds from payer: move from available to held
    balance = _get_or_create_balance(request.payer_user_id)
    if balance["available_egp"] < request.amount_egp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Insufficient available balance for escrow hold",
        )
    balance["available_egp"] -= request.amount_egp
    balance["held_egp"] += request.amount_egp

    _escrows_db[escrow_id] = {
        "escrow_id": escrow_id,
        "shipment_id": request.shipment_id,
        "payer_user_id": request.payer_user_id,
        "amount_egp": request.amount_egp,
        "status": "held",
        "held_at": datetime.now(UTC),
    }

    return EscrowResponse(
        escrow_id=escrow_id,
        status="held",
        amount_egp=request.amount_egp,
    )


@router.post("/escrow/release", response_model=EscrowResponse)
async def release_escrow(request: EscrowReleaseRequest) -> EscrowResponse:
    """Release escrow funds to the recipient (driver)."""
    escrow = _escrows_db.get(request.escrow_id)
    if escrow is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Escrow not found",
        )

    if escrow["status"] != "held":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Escrow is not in 'held' status. Current: {escrow['status']}",
        )

    # Release to recipient
    payer_balance = _get_or_create_balance(escrow["payer_user_id"])
    payer_balance["held_egp"] -= escrow["amount_egp"]
    payer_balance["total_egp"] -= escrow["amount_egp"]

    recipient_balance = _get_or_create_balance(request.release_to_user_id)
    recipient_balance["available_egp"] += escrow["amount_egp"]
    recipient_balance["total_egp"] += escrow["amount_egp"]

    escrow["status"] = "released"
    escrow["released_at"] = datetime.now(UTC)
    escrow["release_to_user_id"] = request.release_to_user_id

    return EscrowResponse(
        escrow_id=request.escrow_id,
        status="released",
        amount_egp=escrow["amount_egp"],
    )


@router.post("/payments", response_model=PaymentResponse)
async def process_payment(request: PaymentRequest) -> PaymentResponse:
    """Process a payment through the specified gateway."""
    tx_id = f"TXN-{uuid.uuid4().hex[:8].upper()}"
    ref_num = f"NQL-PAY-{uuid.uuid4().hex[:6].upper()}"

    # Simulate gateway processing
    gateway_ref = f"{request.payment_method.upper()}-{uuid.uuid4().hex[:10]}"

    transaction = {
        "id": tx_id,
        "reference_number": ref_num,
        "user_id": request.user_id,
        "amount_egp": request.amount_egp,
        "transaction_type": "payment",
        "payment_method": request.payment_method,
        "shipment_id": request.shipment_id,
        "status": "completed",
        "gateway_ref": gateway_ref,
        "created_at": datetime.now(UTC),
    }
    _transactions_db[tx_id] = transaction

    # Update balance
    balance = _get_or_create_balance(request.user_id)
    balance["available_egp"] += request.amount_egp
    balance["total_egp"] += request.amount_egp

    return PaymentResponse(
        transaction_id=tx_id,
        status="completed",
        gateway_ref=gateway_ref,
    )


@router.get("/balance/{user_id}", response_model=BalanceResponse)
async def get_balance(user_id: str) -> BalanceResponse:
    """Get a user's account balance."""
    balance = _get_or_create_balance(user_id)
    return BalanceResponse(**balance)


@router.get("/transactions/{user_id}", response_model=TransactionHistoryResponse)
async def get_transaction_history(
    user_id: str,
    page: int = 1,
    page_size: int = 20,
    transaction_type: str | None = None,
) -> TransactionHistoryResponse:
    """Get a user's transaction history."""
    txns = [t for t in _transactions_db.values() if t["user_id"] == user_id]

    if transaction_type:
        txns = [t for t in txns if t["transaction_type"] == transaction_type]

    total = len(txns)
    start = (page - 1) * page_size
    end = start + page_size
    page_txns = txns[start:end]

    return TransactionHistoryResponse(
        transactions=[
            TransactionRecord(
                id=t["id"],
                reference_number=t["reference_number"],
                amount_egp=t["amount_egp"],
                transaction_type=t["transaction_type"],
                status=t["status"],
                payment_method=t.get("payment_method"),
                created_at=t["created_at"],
            )
            for t in page_txns
        ],
        total=total,
        page=page,
        page_size=page_size,
        has_next=end < total,
    )
