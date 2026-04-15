"""Agent tools — callable functions the AI agent can invoke.

Each tool interfaces with an internal microservice via HTTP.
In production, these would use gRPC for better performance.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from ..core.config import settings


@dataclass
class ToolResult:
    """Result of a tool execution."""

    success: bool
    data: dict[str, Any]
    error: str | None = None


class ServiceClient:
    """HTTP client for internal service communication."""

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(timeout=30.0)

    async def close(self) -> None:
        await self._client.aclose()

    async def _call(self, method: str, url: str, **kwargs: Any) -> ToolResult:
        try:
            response = await self._client.request(method, url, **kwargs)
            response.raise_for_status()
            return ToolResult(success=True, data=response.json())
        except httpx.HTTPStatusError as e:
            return ToolResult(
                success=False,
                data={},
                error=f"HTTP {e.response.status_code}: {e.response.text}",
            )
        except Exception as e:
            return ToolResult(success=False, data={}, error=str(e))

    # ── Fleet Tools ──────────────────────────────────────────

    async def search_available_trucks(
        self,
        latitude: float,
        longitude: float,
        radius_km: float = 20.0,
        truck_type: str | None = None,
        min_capacity_kg: int = 0,
    ) -> ToolResult:
        """Search for available trucks near a location."""
        payload = {
            "center": {"latitude": latitude, "longitude": longitude},
            "radius_km": radius_km,
            "truck_type": truck_type,
            "min_capacity_kg": min_capacity_kg,
        }
        return await self._call(
            "POST",
            f"{settings.MATCHING_SERVICE_URL}/api/v1/match/available-trucks",
            json=payload,
        )

    async def request_match(
        self,
        shipment_id: str,
        origin_lat: float,
        origin_lng: float,
        dest_lat: float,
        dest_lng: float,
        truck_type: str | None = None,
        weight_kg: float = 0.0,
        requires_refrigeration: bool = False,
    ) -> ToolResult:
        """Request a driver/truck match for a shipment."""
        payload = {
            "shipment_id": shipment_id,
            "origin": {"latitude": origin_lat, "longitude": origin_lng},
            "destination": {"latitude": dest_lat, "longitude": dest_lng},
            "required_truck_type": truck_type,
            "weight_kg": weight_kg,
            "requires_refrigeration": requires_refrigeration,
        }
        return await self._call(
            "POST",
            f"{settings.MATCHING_SERVICE_URL}/api/v1/match",
            json=payload,
        )

    # ── Pricing Tools ────────────────────────────────────────

    async def get_quote(
        self,
        distance_km: float,
        truck_type: str,
        weight_kg: float,
        origin_region: str,
        dest_region: str,
        requires_refrigeration: bool = False,
    ) -> ToolResult:
        """Get a price quote for a shipment."""
        payload = {
            "distance_km": distance_km,
            "truck_type": truck_type,
            "weight_kg": weight_kg,
            "origin_region": origin_region,
            "dest_region": dest_region,
            "requires_refrigeration": requires_refrigeration,
        }
        return await self._call(
            "POST",
            f"{settings.FINTRACK_SERVICE_URL}/api/v1/quotes",
            json=payload,
        )

    # ── Escrow Tools ─────────────────────────────────────────

    async def create_escrow(
        self,
        shipment_id: str,
        payer_user_id: str,
        amount_egp: float,
    ) -> ToolResult:
        """Create an escrow hold for a shipment."""
        payload = {
            "shipment_id": shipment_id,
            "payer_user_id": payer_user_id,
            "amount_egp": amount_egp,
        }
        return await self._call(
            "POST",
            f"{settings.FINTRACK_SERVICE_URL}/api/v1/escrow",
            json=payload,
        )

    async def release_escrow(
        self,
        escrow_id: str,
        release_to_user_id: str,
    ) -> ToolResult:
        """Release escrow funds to the driver."""
        payload = {
            "escrow_id": escrow_id,
            "release_to_user_id": release_to_user_id,
        }
        return await self._call(
            "POST",
            f"{settings.FINTRACK_SERVICE_URL}/api/v1/escrow/release",
            json=payload,
        )

    # ── User Tools ───────────────────────────────────────────

    async def get_user(self, user_id: str) -> ToolResult:
        """Get user details."""
        return await self._call(
            "GET",
            f"{settings.IDENTITY_SERVICE_URL}/api/v1/users/{user_id}",
        )

    async def get_truck(self, truck_id: str) -> ToolResult:
        """Get truck details."""
        return await self._call(
            "GET",
            f"{settings.FLEET_SERVICE_URL}/api/v1/trucks/{truck_id}",
        )

    async def get_balance(self, user_id: str) -> ToolResult:
        """Get user account balance."""
        return await self._call(
            "GET",
            f"{settings.FINTRACK_SERVICE_URL}/api/v1/balance/{user_id}",
        )


# Global service client
service_client = ServiceClient()
