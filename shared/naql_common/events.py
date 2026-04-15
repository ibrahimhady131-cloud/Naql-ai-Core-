"""NATS JetStream event bus utilities."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any

import nats
from nats.js.api import StreamConfig, ConsumerConfig


logger = logging.getLogger(__name__)

# NATS server URL - can be overridden via environment
NATS_URL = os.getenv("NATS_URL", "nats://127.0.0.1:4222")

# JetStream stream configuration
STREAM_NAME = "NAQL_EVENTS"
SUBJECTS = ["shipment.>", "telemetry.>", "match.>"]


class NATSClient:
    """Async NATS JetStream client for publishing and subscribing."""

    def __init__(self, url: str = NATS_URL):
        self.url = url
        self._nc = None
        self._js = None
        self._connected = False

    async def connect(self) -> bool:
        """Connect to NATS server and setup JetStream. Returns True if successful."""
        if self._connected:
            return True

        try:
            self._nc = await nats.connect(self.url)
            self._js = self._nc.jetstream()
            self._connected = True
            logger.info(f"[NATS] Connected to {self.url}")

            # Ensure stream exists
            try:
                await self._js.stream_info(STREAM_NAME)
            except Exception:
                # Create stream if it doesn't exist
                await self._js.add_stream(
                    name=STREAM_NAME,
                    subjects=SUBJECTS,
                    config=StreamConfig(
                        retention=StreamConfig.RETAIN_NEW,
                        max_bytes=10_000_000,
                        max_age=86400 * 7,  # 7 days
                    ),
                )
                logger.info(f"[NATS] Created stream: {STREAM_NAME}")

            return True
        except Exception as e:
            logger.warning(f"[NATS] Failed to connect: {e}")
            self._connected = False
            return False

    async def close(self) -> None:
        """Close NATS connection."""
        if self._nc:
            await self._nc.close()
            self._nc = None
            self._js = None

    async def publish(self, subject: str, payload: dict[str, Any]) -> str | None:
        """Publish a message to a subject. Returns None if not connected."""
        if not self._connected:
            success = await self.connect()
            if not success:
                logger.warning(f"[NATS] Cannot publish to {subject} - not connected")
                return None

        try:
            data = json.dumps(payload).encode()
            ack = await self._js.publish(subject, data)
            return ack.seq
        except Exception as e:
            logger.warning(f"[NATS] Publish failed: {e}")
            return None

    async def subscribe(
        self,
        subject: str,
        queue: str | None = None,
        durable: str | None = None,
    ) -> nats.js.client.JetStreamContext:
        """Subscribe to a subject with optional queue and durability."""
        if self._js is None:
            await self.connect()

        config = ConsumerConfig(
            deliver_policy=ConsumerConfig.DeliverPolicy.NEW,
            durable_name=durable,
        )

        if queue:
            sub = await self._js.subscribe(subject, queue=queue, config=config)
        else:
            sub = await self._js.subscribe(subject, config=config)

        return sub


# Global client instance
_nats_client: NATSClient | None = None


async def get_nats_client() -> NATSClient:
    """Get or create the global NATS client."""
    global _nats_client
    if _nats_client is None:
        _nats_client = NATSClient()
        await _nats_client.connect()
    return _nats_client


async def close_nats_client() -> None:
    """Close the global NATS client."""
    global _nats_client
    if _nats_client is not None:
        await _nats_client.close()
        _nats_client = None


async def publish_shipment_created(
    shipment_id: str,
    pickup_h3: str,
    dropoff_h3: str,
    cargo_type: str,
) -> str | None:
    """Publish a shipment.created event. Returns None if NATS unavailable."""
    client = await get_nats_client()
    payload = {
        "event": "shipment.created",
        "shipment_id": shipment_id,
        "pickup_h3": pickup_h3,
        "dropoff_h3": dropoff_h3,
        "cargo_type": cargo_type,
    }
    seq = await client.publish("shipment.created", payload)
    if seq:
        logger.info(f"[NATS] Published shipment.created for {shipment_id}, seq={seq}")
    return str(seq) if seq else None
