"""Shared utility functions and constants."""

from __future__ import annotations

from enum import StrEnum


class ShipmentStatus(StrEnum):
    """State machine for shipment lifecycle."""

    DRAFT = "draft"
    QUOTED = "quoted"
    CONFIRMED = "confirmed"
    ASSIGNED = "assigned"
    DRIVER_EN_ROUTE = "driver_en_route"
    PICKED_UP = "picked_up"
    IN_TRANSIT = "in_transit"
    NEAR_DESTINATION = "near_destination"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    DISPUTED = "disputed"


class TruckType(StrEnum):
    """Egyptian market truck categories."""

    QUARTER_LOAD = "quarter"  # ربع نقل
    HALF_LOAD = "half"  # نص نقل
    FULL_LOAD = "full"  # نقل كامل
    JUMBO = "jumbo"  # جامبو
    TRAILER = "trailer"  # مقطوره
    REFRIGERATED = "refrigerated"  # مبرد
    TANKER = "tanker"  # تانكر
    FLATBED = "flatbed"  # مسطح


class TruckStatus(StrEnum):
    """Real-time truck availability status."""

    AVAILABLE = "available"
    EN_ROUTE = "en_route"
    LOADING = "loading"
    UNLOADING = "unloading"
    MAINTENANCE = "maintenance"
    OFFLINE = "offline"


class PaymentMethod(StrEnum):
    """Egyptian payment methods."""

    FAWRY = "fawry"
    PAYMOB = "paymob"
    VALU = "valu"
    BANK_TRANSFER = "bank_transfer"
    CASH_ON_DELIVERY = "cash_on_delivery"
    ENTERPRISE_CREDIT = "enterprise_credit"


class KYCStatus(StrEnum):
    """Know Your Customer verification status."""

    PENDING = "pending"
    DOCUMENTS_SUBMITTED = "documents_submitted"
    UNDER_REVIEW = "under_review"
    VERIFIED = "verified"
    REJECTED = "rejected"


# Valid state transitions for shipment state machine
VALID_TRANSITIONS: dict[ShipmentStatus, list[ShipmentStatus]] = {
    ShipmentStatus.DRAFT: [ShipmentStatus.QUOTED, ShipmentStatus.CANCELLED],
    ShipmentStatus.QUOTED: [ShipmentStatus.CONFIRMED, ShipmentStatus.CANCELLED],
    ShipmentStatus.CONFIRMED: [ShipmentStatus.ASSIGNED, ShipmentStatus.CANCELLED],
    ShipmentStatus.ASSIGNED: [
        ShipmentStatus.DRIVER_EN_ROUTE,
        ShipmentStatus.CANCELLED,
    ],
    ShipmentStatus.DRIVER_EN_ROUTE: [
        ShipmentStatus.PICKED_UP,
        ShipmentStatus.CANCELLED,
    ],
    ShipmentStatus.PICKED_UP: [ShipmentStatus.IN_TRANSIT],
    ShipmentStatus.IN_TRANSIT: [
        ShipmentStatus.NEAR_DESTINATION,
        ShipmentStatus.DELIVERED,
        ShipmentStatus.DISPUTED,
    ],
    ShipmentStatus.NEAR_DESTINATION: [
        ShipmentStatus.DELIVERED,
        ShipmentStatus.DISPUTED,
    ],
    ShipmentStatus.DELIVERED: [ShipmentStatus.DISPUTED],
    ShipmentStatus.CANCELLED: [],
    ShipmentStatus.DISPUTED: [],
}


# Load capacities in kg per truck type
TRUCK_CAPACITIES: dict[TruckType, int] = {
    TruckType.QUARTER_LOAD: 1_500,
    TruckType.HALF_LOAD: 3_000,
    TruckType.FULL_LOAD: 7_000,
    TruckType.JUMBO: 15_000,
    TruckType.TRAILER: 25_000,
    TruckType.REFRIGERATED: 12_000,
    TruckType.TANKER: 20_000,
    TruckType.FLATBED: 18_000,
}
