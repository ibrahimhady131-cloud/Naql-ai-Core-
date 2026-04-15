"""HTTP client for internal service communication from the GraphQL Gateway."""

from __future__ import annotations

import os
from typing import Any

import httpx


class ServiceClient:
    """Synchronous HTTP client that proxies GraphQL requests to internal microservices."""

    def __init__(self) -> None:
        self._identity_url = os.getenv("GATEWAY_IDENTITY_SERVICE_URL", "http://localhost:8001")
        self._fleet_url = os.getenv("GATEWAY_FLEET_SERVICE_URL", "http://localhost:8002")
        self._matching_url = os.getenv("GATEWAY_MATCHING_SERVICE_URL", "http://localhost:8003")
        self._fintrack_url = os.getenv("GATEWAY_FINTRACK_SERVICE_URL", "http://localhost:8004")
        self._agent_url = os.getenv("GATEWAY_AGENT_SERVICE_URL", "http://localhost:8005")
        self._telemetry_url = os.getenv("GATEWAY_TELEMETRY_SERVICE_URL", "http://localhost:8006")
        self._client = httpx.Client(timeout=30.0)

    def close(self) -> None:
        self._client.close()

    # -- Identity Service --------------------------------------------------------

    def register(self, data: dict[str, Any]) -> dict[str, Any]:
        """POST /api/v1/auth/register -> Identity Service."""
        resp = self._client.post(f"{self._identity_url}/api/v1/auth/register", json=data)
        resp.raise_for_status()
        return resp.json()

    def login(self, email: str, password: str) -> dict[str, Any]:
        """POST /api/v1/auth/login -> Identity Service."""
        resp = self._client.post(
            f"{self._identity_url}/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        resp.raise_for_status()
        return resp.json()

    def get_user(self, user_id: str) -> dict[str, Any] | None:
        """GET /api/v1/users/{user_id} -> Identity Service."""
        resp = self._client.get(f"{self._identity_url}/api/v1/users/{user_id}")
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()

    def get_me(self, token: str) -> dict[str, Any] | None:
        """GET /api/v1/users/me -> Identity Service (authenticated)."""
        resp = self._client.get(
            f"{self._identity_url}/api/v1/users/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        if resp.status_code == 401:
            return None
        resp.raise_for_status()
        return resp.json()

    # -- Fleet Service ---------------------------------------------------------

    def get_truck(self, truck_id: str) -> dict[str, Any] | None:
        """GET /api/v1/trucks/{truck_id} -> Fleet Service."""
        resp = self._client.get(f"{self._fleet_url}/api/v1/trucks/{truck_id}")
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()

    def list_trucks(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        truck_type: str | None = None,
        region_code: str | None = None,
    ) -> list[dict[str, Any]]:
        """GET /api/v1/trucks -> Fleet Service."""
        params: dict[str, Any] = {"page": page, "page_size": page_size}
        if truck_type:
            params["truck_type"] = truck_type
        if region_code:
            params["region_code"] = region_code
        resp = self._client.get(f"{self._fleet_url}/api/v1/trucks", params=params)
        resp.raise_for_status()
        data = resp.json()
        return data.get("trucks", [])

    # -- Matching Engine ---------------------------------------------------------

    def get_shipment(self, shipment_id: str) -> dict[str, Any] | None:
        """GET /api/v1/shipments/{shipment_id} -> Matching Engine."""
        resp = self._client.get(f"{self._matching_url}/api/v1/shipments/{shipment_id}")
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()

    def list_shipments(self, client_id: str | None = None, status: str | None = None) -> list[dict[str, Any]]:
        """GET /api/v1/shipments -> Matching Engine."""
        params: dict[str, Any] = {}
        if client_id:
            params["client_id"] = client_id
        if status:
            params["status"] = status
        resp = self._client.get(f"{self._matching_url}/api/v1/shipments", params=params)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list):
            return data
        return data.get("shipments", [])

    def request_match(self, data: dict[str, Any]) -> dict[str, Any]:
        """POST /api/v1/match -> Matching Engine."""
        resp = self._client.post(f"{self._matching_url}/api/v1/match", json=data)
        resp.raise_for_status()
        return resp.json()

    # -- FinTrack Service --------------------------------------------------------

    def get_balance(self, user_id: str) -> dict[str, Any] | None:
        """GET /api/v1/balance/{user_id} -> FinTrack Service."""
        resp = self._client.get(
            f"{self._fintrack_url}/api/v1/balance/{user_id}"
        )
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()

    def get_quote(self, data: dict[str, Any]) -> dict[str, Any]:
        """POST /api/v1/quotes -> FinTrack Service."""
        resp = self._client.post(
            f"{self._fintrack_url}/api/v1/quotes", json=data
        )
        resp.raise_for_status()
        return resp.json()

    # -- Agent Orchestrator --------------------------------------------------------

    def chat(self, data: dict[str, Any]) -> dict[str, Any]:
        """POST /api/v1/chat -> Agent Orchestrator."""
        resp = self._client.post(f"{self._agent_url}/api/v1/chat", json=data)
        resp.raise_for_status()
        return resp.json()

    # -- Telemetry Service --------------------------------------------------------

    def get_latest_positions(self, truck_id: str, limit: int = 1) -> dict[str, Any]:
        """GET /telemetry/truck/{truck_id} -> Telemetry Ingress."""
        resp = self._client.get(
            f"{self._telemetry_url}/telemetry/truck/{truck_id}",
            params={"limit": limit},
        )
        resp.raise_for_status()
        return resp.json()

    def get_trip_history(self, shipment_id: str) -> list[dict[str, Any]]:
        """GET /api/v1/trips/{shipment_id}/history -> Matching Engine."""
        resp = self._client.get(f"{self._matching_url}/api/v1/trips/{shipment_id}/history")
        if resp.status_code == 404:
            return []
        resp.raise_for_status()
        data = resp.json()
        return data.get("positions", [])

    def get_ai_reasoning(self, shipment_id: str) -> list[dict[str, Any]]:
        """GET /api/v1/shipments/{shipment_id}/ai_reasoning -> Matching Engine."""
        resp = self._client.get(f"{self._matching_url}/api/v1/shipments/{shipment_id}/ai_reasoning")
        if resp.status_code == 404:
            return []
        resp.raise_for_status()
        data = resp.json()
        return data.get("reasoning", [])

    # -- FinTrack Service (Payments) ----------------------------------------------

    def create_payment_link(self, invoice_id: str, amount_egp: float, user_id: str) -> dict[str, Any]:
        """POST /api/v1/payments/link -> FinTrack Service (via Gateway)."""
        params = {
            "invoice_id": invoice_id,
            "amount_egp": amount_egp,
            "user_id": user_id,
            "payment_method": "paymob",
        }
        resp = self._client.post(f"{self._fintrack_url}/api/v1/payments/link", params=params)
        resp.raise_for_status()
        return resp.json()
