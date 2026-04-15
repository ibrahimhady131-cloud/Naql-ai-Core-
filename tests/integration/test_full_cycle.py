"""Integration tests for the full Naql.ai shipment lifecycle.

Tests the complete flow:
  User registers -> Agent classifies intent -> Matching Engine finds truck ->
  Pricing Engine quotes -> FinTrack escrow -> Telemetry updates -> Trip completes

All tests run against in-memory service instances (no real DB required).
"""

from __future__ import annotations

import random
import uuid

import pytest
from fastapi.testclient import TestClient


def _egyptian_phone() -> str:
    """Generate a valid Egyptian phone number (+20 + 10 digits)."""
    return f"+20{''.join(str(random.randint(0, 9)) for _ in range(10))}"


# ── Identity Service Tests ──────────────────────────────────────────


@pytest.fixture
def identity_client():
    """Create a test client for the Identity Service."""
    import importlib
    import sys

    svc_dir = "services/identity-service"
    stale = [k for k in sys.modules if k == "app" or k.startswith("app.")]
    for k in stale:
        del sys.modules[k]
    sys.path.insert(0, svc_dir)
    try:
        mod = importlib.import_module("app.main")
    finally:
        sys.path.remove(svc_dir)
    return TestClient(mod.app)


def test_user_registration(identity_client):
    """Test: User can register and receive JWT tokens."""
    resp = identity_client.post("/api/v1/auth/register", json={
        "email": f"test-{uuid.uuid4().hex[:8]}@naql.ai",
        "phone": _egyptian_phone(),
        "password": "SecurePass123!",
        "full_name": "Ahmed Test",
        "role": "client_individual",
        "region_code": "EG-CAI",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["role"] == "client_individual"
    assert data["region_code"] == "EG-CAI"


def test_duplicate_email_rejected(identity_client):
    """Test: Duplicate email registration returns 409."""
    email = f"dup-{uuid.uuid4().hex[:8]}@naql.ai"

    resp1 = identity_client.post("/api/v1/auth/register", json={
        "email": email,
        "phone": _egyptian_phone(),
        "password": "Pass1234!",
        "full_name": "First User",
        "role": "client_individual",
        "region_code": "EG-CAI",
    })
    assert resp1.status_code == 201

    resp2 = identity_client.post("/api/v1/auth/register", json={
        "email": email,
        "phone": _egyptian_phone(),
        "password": "Pass5678!",
        "full_name": "Second User",
        "role": "client_individual",
        "region_code": "EG-CAI",
    })
    assert resp2.status_code == 409


def test_duplicate_phone_rejected(identity_client):
    """Test: Duplicate phone registration returns 409."""
    phone = _egyptian_phone()

    identity_client.post("/api/v1/auth/register", json={
        "email": f"u1-{uuid.uuid4().hex[:8]}@naql.ai",
        "phone": phone,
        "password": "Pass1234!",
        "full_name": "First",
        "role": "client_individual",
        "region_code": "EG-CAI",
    })

    resp = identity_client.post("/api/v1/auth/register", json={
        "email": f"u2-{uuid.uuid4().hex[:8]}@naql.ai",
        "phone": phone,
        "password": "Pass5678!",
        "full_name": "Second",
        "role": "client_individual",
        "region_code": "EG-CAI",
    })
    assert resp.status_code == 409


def test_login_flow(identity_client):
    """Test: User can login with correct credentials."""
    email = f"login-{uuid.uuid4().hex[:8]}@naql.ai"
    password = "LoginPass123!"

    identity_client.post("/api/v1/auth/register", json={
        "email": email,
        "phone": _egyptian_phone(),
        "password": password,
        "full_name": "Login User",
        "role": "driver",
        "region_code": "EG-SUE",
    })

    resp = identity_client.post("/api/v1/auth/login", json={
        "email": email,
        "password": password,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["role"] == "driver"


def test_role_restriction(identity_client):
    """Test: Self-registration rejects admin/ops roles."""
    resp = identity_client.post("/api/v1/auth/register", json={
        "email": f"admin-{uuid.uuid4().hex[:8]}@naql.ai",
        "phone": _egyptian_phone(),
        "password": "Pass1234!",
        "full_name": "Sneaky Admin",
        "role": "admin",
        "region_code": "EG-CAI",
    })
    assert resp.status_code == 422  # Pydantic validation error


# ── FinTrack Service Tests ──────────────────────────────────────────


@pytest.fixture
def fintrack_client():
    """Create a test client for the FinTrack Service."""
    import importlib
    import sys

    stale = [k for k in sys.modules if k == "app" or k.startswith("app.")]
    for k in stale:
        del sys.modules[k]
    sys.path.insert(0, "services/fintrack-service")
    try:
        mod = importlib.import_module("app.main")
    finally:
        sys.path.remove("services/fintrack-service")
    return TestClient(mod.app)


def test_price_quote(fintrack_client):
    """Test: Pricing engine generates valid quote for Sokhna->October route."""
    resp = fintrack_client.post("/api/v1/quotes", json={
        "distance_km": 142.3,
        "truck_type": "trailer",
        "weight_kg": 30000,
        "origin_region": "EG-SOK",
        "dest_region": "EG-OCT",
        "requires_refrigeration": False,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_egp"] > 0
    assert data["fuel_cost_egp"] > 0
    assert data["toll_cost_egp"] > 0
    assert "quote_id" in data


def test_escrow_lifecycle(fintrack_client):
    """Test: Escrow hold and release flow."""
    user_id = f"USR-{uuid.uuid4().hex[:8]}"
    driver_id = f"DRV-{uuid.uuid4().hex[:8]}"
    shipment_id = f"SHP-{uuid.uuid4().hex[:8]}"

    # Fund user's wallet
    resp = fintrack_client.post("/api/v1/payments", json={
        "user_id": user_id,
        "amount_egp": 5000.0,
        "payment_method": "fawry",
        "shipment_id": shipment_id,
    })
    assert resp.status_code == 200

    # Check balance
    resp = fintrack_client.get(f"/api/v1/balance/{user_id}")
    assert resp.status_code == 200
    assert resp.json()["available_egp"] == 5000.0

    # Create escrow hold
    resp = fintrack_client.post("/api/v1/escrow", json={
        "shipment_id": shipment_id,
        "payer_user_id": user_id,
        "amount_egp": 2000.0,
    })
    assert resp.status_code == 201
    escrow_id = resp.json()["escrow_id"]

    # Check balance after escrow
    resp = fintrack_client.get(f"/api/v1/balance/{user_id}")
    balance = resp.json()
    assert balance["available_egp"] == 3000.0
    assert balance["held_egp"] == 2000.0

    # Release escrow to driver
    resp = fintrack_client.post("/api/v1/escrow/release", json={
        "escrow_id": escrow_id,
        "release_to_user_id": driver_id,
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "released"

    # Driver should have received funds
    resp = fintrack_client.get(f"/api/v1/balance/{driver_id}")
    assert resp.json()["available_egp"] == 2000.0


def test_insufficient_funds_escrow(fintrack_client):
    """Test: Escrow creation fails with insufficient balance."""
    user_id = f"BROKE-{uuid.uuid4().hex[:8]}"

    resp = fintrack_client.post("/api/v1/escrow", json={
        "shipment_id": f"SHP-{uuid.uuid4().hex[:8]}",
        "payer_user_id": user_id,
        "amount_egp": 10000.0,
    })
    assert resp.status_code == 400


# ── Telemetry Ingress Tests ─────────────────────────────────────────


@pytest.fixture
def telemetry_client():
    """Create a test client for the Telemetry Ingress Service."""
    import importlib
    import sys

    stale = [k for k in sys.modules if k == "app" or k.startswith("app.")]
    for k in stale:
        del sys.modules[k]
    sys.path.insert(0, "services/telemetry-ingress")
    try:
        mod = importlib.import_module("app.main")
    finally:
        sys.path.remove("services/telemetry-ingress")
    return TestClient(mod.app)


def test_position_ingestion(telemetry_client):
    """Test: GPS position data is accepted and processed."""
    resp = telemetry_client.post("/api/v1/ingest/position", json={
        "truck_id": f"TRK-{uuid.uuid4().hex[:8]}",
        "driver_id": f"DRV-{uuid.uuid4().hex[:8]}",
        "trip_id": None,
        "latitude": 29.9569,
        "longitude": 30.9271,
        "speed_kmh": 80.0,
        "heading": 270.0,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["received"] is True


def test_geofence_detection(telemetry_client):
    """Test: Entering a geofence hub generates an event."""
    truck_id = f"TRK-{uuid.uuid4().hex[:8]}"

    # Send position inside Sokhna Port geofence
    resp = telemetry_client.post("/api/v1/ingest/position", json={
        "truck_id": truck_id,
        "latitude": 29.5952,
        "longitude": 32.3414,
        "speed_kmh": 10.0,
    })
    assert resp.status_code == 200
    data = resp.json()
    # Should generate a geofence_entered event for sokhna_port
    geofence_events = [e for e in data["events"] if e["type"] == "geofence_entered"]
    assert len(geofence_events) >= 1
    assert geofence_events[0]["hub"] == "sokhna_port"


def test_speed_violation(telemetry_client):
    """Test: Speed over 120 km/h generates a violation event."""
    resp = telemetry_client.post("/api/v1/ingest/position", json={
        "truck_id": f"SPEED-{uuid.uuid4().hex[:8]}",
        "latitude": 30.0,
        "longitude": 31.0,
        "speed_kmh": 135.0,
    })
    assert resp.status_code == 200
    violations = [e for e in resp.json()["events"] if e["type"] == "speed_violation"]
    assert len(violations) == 1
    assert violations[0]["speed_kmh"] == 135.0


def test_telemetry_ingestion(telemetry_client):
    """Test: OBD-II sensor data is accepted."""
    resp = telemetry_client.post("/api/v1/ingest/telemetry", json={
        "truck_id": f"TRK-{uuid.uuid4().hex[:8]}",
        "engine_rpm": 2500,
        "engine_temp_c": 85.0,
        "fuel_level_pct": 65.0,
        "fuel_rate_lph": 12.5,
        "odometer_km": 150000.0,
        "battery_voltage": 12.6,
        "cargo_temp_c": None,
        "harsh_braking": False,
        "harsh_acceleration": False,
        "sharp_turn": False,
    })
    assert resp.status_code == 200
    assert resp.json()["received"] is True


def test_engine_overheat_alert(telemetry_client):
    """Test: Engine temperature > 110C generates overheat alert."""
    resp = telemetry_client.post("/api/v1/ingest/telemetry", json={
        "truck_id": f"HOT-{uuid.uuid4().hex[:8]}",
        "engine_temp_c": 115.0,
        "engine_rpm": 3000,
    })
    assert resp.status_code == 200
    alerts = [e for e in resp.json()["events"] if e["type"] == "engine_overheat"]
    assert len(alerts) == 1
    assert alerts[0]["severity"] == "critical"


# ── Fleet Service Tests ─────────────────────────────────────────────


@pytest.fixture
def fleet_client():
    """Create a test client for the Fleet Service."""
    import importlib
    import sys

    stale = [k for k in sys.modules if k == "app" or k.startswith("app.")]
    for k in stale:
        del sys.modules[k]
    sys.path.insert(0, "services/fleet-service")
    try:
        mod = importlib.import_module("app.main")
    finally:
        sys.path.remove("services/fleet-service")
    return TestClient(mod.app)


def test_truck_registration(fleet_client):
    """Test: A truck can be registered in the fleet."""
    resp = fleet_client.post("/api/v1/trucks", json={
        "owner_id": str(uuid.uuid4()),
        "license_plate": f"ABC {uuid.uuid4().hex[:4].upper()}",
        "truck_type": "trailer",
        "load_capacity_kg": 25000,
        "region_code": "EG-SUE",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["truck_type"] == "trailer"
    assert data["status"] == "offline"


def test_truck_status_update(fleet_client):
    """Test: Truck status can be updated (offline -> available)."""
    # Register a truck
    resp = fleet_client.post("/api/v1/trucks", json={
        "owner_id": str(uuid.uuid4()),
        "license_plate": f"XYZ {uuid.uuid4().hex[:4].upper()}",
        "truck_type": "jumbo",
        "load_capacity_kg": 15000,
        "region_code": "EG-CAI",
    })
    truck_id = resp.json()["id"]

    # Update status to available
    resp = fleet_client.patch(f"/api/v1/trucks/{truck_id}/status", json={
        "status": "available",
        "latitude": 30.0444,
        "longitude": 31.2357,
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "available"


# ── Matching Engine Tests ───────────────────────────────────────────


@pytest.fixture
def matching_client():
    """Create a test client for the Matching Engine."""
    import importlib
    import sys

    stale = [k for k in sys.modules if k == "app" or k.startswith("app.")]
    for k in stale:
        del sys.modules[k]
    sys.path.insert(0, "services/matching-engine")
    try:
        mod = importlib.import_module("app.main")
    finally:
        sys.path.remove("services/matching-engine")
    return TestClient(mod.app)


def test_health_check(matching_client):
    """Test: Matching engine health endpoint responds."""
    resp = matching_client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


# ── Cross-Service Integration ───────────────────────────────────────


def test_full_lifecycle_pricing():
    """Integration test: Full pricing quote validates Cartas for known Egyptian routes."""
    import importlib
    import sys

    from naql_common.utils import TruckType

    stale = [k for k in sys.modules if k == "app" or k.startswith("app.")]
    for k in stale:
        del sys.modules[k]
    sys.path.insert(0, "services/fintrack-service")
    try:
        pricing = importlib.import_module("app.core.pricing")
    finally:
        sys.path.remove("services/fintrack-service")

    # Sokhna -> October (the primary simulation route)
    quote = pricing.calculate_quote(
        distance_km=142.3,
        truck_type=TruckType.TRAILER,
        weight_kg=30000,
        origin_region="EG-SOK",
        dest_region="EG-OCT",
    )
    assert quote.total_egp > 0
    assert quote.toll_cost_egp == 480.0  # 320 base * 1.5 trailer multiplier
    assert quote.fuel_cost_egp > 3000  # 142.3 km * 22.0 * weight factor
    assert 4500 <= quote.total_egp <= 6500  # 2025 market rate for Sokhna->October

    # Cairo -> Alexandria
    quote_alex = pricing.calculate_quote(
        distance_km=220.0,
        truck_type=TruckType.FULL_LOAD,
        weight_kg=7000,
        origin_region="EG-CAI",
        dest_region="EG-ALX",
    )
    assert quote_alex.toll_cost_egp == 450.0  # Full load multiplier = 1.0
    assert quote_alex.total_egp > quote.toll_cost_egp
