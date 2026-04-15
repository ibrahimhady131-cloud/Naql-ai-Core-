"""ORM models package."""

from __future__ import annotations

from importlib import import_module
from typing import Any

_MODEL_MODULES = {
    "ApiKey": "identity",
    "DriverPreferences": "shipment",
    "DrivingViolation": "telemetry",
    "EscrowHold": "fintrack",
    "GeofenceEvent": "telemetry",
    "LedgerAccount": "fintrack",
    "MatchHistory": "shipment",
    "Notification": "notification",
    "Shipment": "shipment",
    "ShipmentAuditLog": "shipment",
    "Transaction": "fintrack",
    "Trip": "shipment",
    "Truck": "fleet",
    "TruckMaintenance": "fleet",
    "TruckPosition": "telemetry",
    "TruckTelemetry": "telemetry",
    "User": "identity",
    "UserDocument": "identity",
}


def __getattr__(name: str) -> Any:
    if name not in _MODEL_MODULES:
        raise AttributeError(name)
    module = import_module(f"naql_common.db.models.{_MODEL_MODULES[name]}")
    value = getattr(module, name)
    globals()[name] = value
    return value

__all__ = [
    "ApiKey",
    "DriverPreferences",
    "DrivingViolation",
    "EscrowHold",
    "GeofenceEvent",
    "LedgerAccount",
    "MatchHistory",
    "Notification",
    "Shipment",
    "ShipmentAuditLog",
    "Transaction",
    "Trip",
    "Truck",
    "TruckMaintenance",
    "TruckPosition",
    "TruckTelemetry",
    "User",
    "UserDocument",
]
