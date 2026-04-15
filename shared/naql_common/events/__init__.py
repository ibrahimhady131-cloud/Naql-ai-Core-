"""NATS JetStream event bus for async inter-service communication."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

import nats
from nats.aio.client import Client as NATSClient
from nats.js import JetStreamContext


class EventType(StrEnum):
    """All domain events in the Naql.ai ecosystem."""

    # Identity events
    USER_REGISTERED = "identity.user.registered"
    USER_VERIFIED = "identity.user.verified"
    USER_SUSPENDED = "identity.user.suspended"

    # Fleet events
    TRUCK_REGISTERED = "fleet.truck.registered"
    TRUCK_LOCATION_UPDATED = "fleet.truck.location_updated"
    TRUCK_STATUS_CHANGED = "fleet.truck.status_changed"
    TRUCK_MAINTENANCE_DUE = "fleet.truck.maintenance_due"

    # Matching events
    MATCH_REQUESTED = "matching.match.requested"
    MATCH_FOUND = "matching.match.found"
    MATCH_REJECTED = "matching.match.rejected"
    MATCH_EXPIRED = "matching.match.expired"

    # Shipment events
    SHIPMENT_CREATED = "shipment.created"
    SHIPMENT_ASSIGNED = "shipment.assigned"
    SHIPMENT_PICKED_UP = "shipment.picked_up"
    SHIPMENT_IN_TRANSIT = "shipment.in_transit"
    SHIPMENT_DELIVERED = "shipment.delivered"
    SHIPMENT_CANCELLED = "shipment.cancelled"

    # Financial events
    PAYMENT_INITIATED = "fintrack.payment.initiated"
    PAYMENT_COMPLETED = "fintrack.payment.completed"
    ESCROW_CREATED = "fintrack.escrow.created"
    ESCROW_RELEASED = "fintrack.escrow.released"

    # Agent events
    AGENT_TASK_CREATED = "agent.task.created"
    AGENT_TASK_COMPLETED = "agent.task.completed"
    AGENT_ALERT_TRIGGERED = "agent.alert.triggered"

    # Telemetry events
    GEOFENCE_ENTERED = "telemetry.geofence.entered"
    GEOFENCE_EXITED = "telemetry.geofence.exited"
    SPEED_VIOLATION = "telemetry.speed.violation"
    ROUTE_DEVIATION = "telemetry.route.deviation"


@dataclass
class DomainEvent:
    """Represents a domain event in the system."""

    event_type: EventType
    payload: dict[str, Any]
    event_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    source_service: str = ""
    correlation_id: str = ""
    region_code: str = ""

    def to_bytes(self) -> bytes:
        """Serialize event to bytes for NATS publishing."""
        return json.dumps(
            {
                "event_id": self.event_id,
                "event_type": self.event_type,
                "timestamp": self.timestamp,
                "source_service": self.source_service,
                "correlation_id": self.correlation_id,
                "region_code": self.region_code,
                "payload": self.payload,
            }
        ).encode("utf-8")

    @classmethod
    def from_bytes(cls, data: bytes) -> DomainEvent:
        """Deserialize event from bytes."""
        raw = json.loads(data.decode("utf-8"))
        return cls(
            event_id=raw["event_id"],
            event_type=EventType(raw["event_type"]),
            timestamp=raw["timestamp"],
            source_service=raw.get("source_service", ""),
            correlation_id=raw.get("correlation_id", ""),
            region_code=raw.get("region_code", ""),
            payload=raw["payload"],
        )


class EventBus:
    """NATS JetStream-based event bus for pub/sub messaging."""

    def __init__(self, nats_url: str = "nats://127.0.0.1:4222") -> None:
        self._nats_url = nats_url
        self._nc: NATSClient | None = None
        self._js: JetStreamContext | None = None

    async def connect(self) -> None:
        """Connect to NATS and initialize JetStream."""
        self._nc = await nats.connect(
            self._nats_url,
            connect_timeout=10,
            reconnect_time_wait=2,
            max_reconnect_attempts=5,
        )
        self._js = self._nc.jetstream()

        # Create core streams
        for stream_name, subjects in [
            ("IDENTITY", ["identity.>"]),
            ("FLEET", ["fleet.>"]),
            ("MATCHING", ["matching.>"]),
            ("SHIPMENT", ["shipment.>"]),
            ("FINTRACK", ["fintrack.>"]),
            ("AGENT", ["agent.>"]),
            ("TELEMETRY", ["telemetry.>"]),
        ]:
            await self._js.add_stream(
                name=stream_name,
                subjects=subjects,
                retention="limits",
                max_age=7 * 24 * 3600,  # 7 days retention
            )

    async def publish(self, event: DomainEvent) -> None:
        """Publish a domain event to NATS JetStream."""
        if self._js is None:
            raise RuntimeError("EventBus not connected. Call connect() first.")
        await self._js.publish(
            subject=event.event_type.value,
            payload=event.to_bytes(),
        )

    async def close(self) -> None:
        """Close the NATS connection."""
        if self._nc is not None:
            await self._nc.close()


# Global event bus instance
_event_bus: EventBus | None = None


async def get_event_bus() -> EventBus:
    """Get or create the global EventBus instance."""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
        await _event_bus.connect()
    return _event_bus


async def publish_shipment_created(
    shipment_id: str,
    pickup_h3: str,
    dropoff_h3: str,
    cargo_type: str,
) -> None:
    """Publish a shipment.created event."""
    event_bus = await get_event_bus()
    event = DomainEvent(
        event_type=EventType.SHIPMENT_CREATED,
        source_service="matching-engine",
        payload={
            "shipment_id": shipment_id,
            "pickup_h3": pickup_h3,
            "dropoff_h3": dropoff_h3,
            "cargo_type": cargo_type,
        },
    )
    await event_bus.publish(event)
