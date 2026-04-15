"""Pydantic schemas for FinTrack Service API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class QuoteRequest(BaseModel):
    """Request schema for generating a price quote."""

    distance_km: float = Field(..., gt=0)
    truck_type: str = Field(
        ...,
        pattern=r"^(quarter|half|full|jumbo|trailer|refrigerated|tanker|flatbed)$",
    )
    weight_kg: float = Field(..., gt=0)
    requires_refrigeration: bool = False
    origin_region: str = Field(..., pattern=r"^EG-[A-Z]{3}$")
    dest_region: str = Field(..., pattern=r"^EG-[A-Z]{3}$")


class QuoteResponse(BaseModel):
    """Response schema for price quote."""

    quote_id: str
    total_egp: float
    fuel_cost_egp: float
    toll_cost_egp: float
    service_fee_egp: float
    insurance_fee_egp: float
    valid_until: datetime


class EscrowCreateRequest(BaseModel):
    """Request schema for creating an escrow hold."""

    shipment_id: str
    payer_user_id: str
    amount_egp: float = Field(..., gt=0)


class EscrowResponse(BaseModel):
    """Response schema for escrow operations."""

    escrow_id: str
    status: str
    amount_egp: float


class EscrowReleaseRequest(BaseModel):
    """Request schema for releasing escrow."""

    escrow_id: str
    release_to_user_id: str


class PaymentRequest(BaseModel):
    """Request schema for processing a payment."""

    user_id: str
    amount_egp: float = Field(..., gt=0)
    payment_method: str = Field(
        ...,
        pattern=r"^(fawry|paymob|valu|bank_transfer|cash_on_delivery|enterprise_credit)$",
    )
    shipment_id: str


class PaymentResponse(BaseModel):
    """Response schema for payment processing."""

    transaction_id: str
    status: str
    gateway_ref: str | None = None


class BalanceResponse(BaseModel):
    """Response schema for account balance."""

    user_id: str
    available_egp: float
    held_egp: float
    total_egp: float


class TransactionRecord(BaseModel):
    """Response schema for a transaction record."""

    id: str
    reference_number: str
    amount_egp: float
    transaction_type: str
    status: str
    payment_method: str | None = None
    created_at: datetime


class TransactionHistoryResponse(BaseModel):
    """Paginated transaction history response."""

    transactions: list[TransactionRecord]
    total: int
    page: int
    page_size: int
    has_next: bool


class InvoiceCreateRequest(BaseModel):
    """Request schema for creating an invoice."""

    shipment_id: str
    total_amount_egp: float = Field(..., gt=0)


class InvoiceResponse(BaseModel):
    """Response schema for invoice."""

    id: str
    shipment_id: str
    total_amount_egp: float
    status: str
    created_at: datetime | None = None
