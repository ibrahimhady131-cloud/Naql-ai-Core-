#!/usr/bin/env python3
"""Naql.ai End-to-End Trip Simulation: Sokhna Port → 6th of October City.

Scenario:
    A B2B client needs to move 30 tons of steel from Sokhna Port
    to an industrial site in 6th of October City.

Flow:
    1. Register B2B client & seed driver fleet near Sokhna
    2. AI Agent processes the natural language booking request
    3. Matching Engine finds nearest Trailer (Heavy Truck)
    4. Pricing Engine calculates Cartas (Tolls) on Regional Ring Road
    5. FinTrack creates Escrow transaction
    6. Telemetry Ingress simulates GPS waypoints along the route
    7. Sentinel monitors for anomalies (geofence, speed, ETA)
    8. Route Optimizer plans the optimal path
    9. Full event log output for verification

Usage:
    cd /path/to/BIG-DEV
    python scripts/simulate_trip.py
"""

from __future__ import annotations

import asyncio
import importlib
import importlib.util
import json
import sys
import time
import types
import uuid
from datetime import UTC, datetime
from pathlib import Path

# ══════════════════════════════════════════════════════════════
# Dynamic Service Importer
# ══════════════════════════════════════════════════════════════

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Shared library must be on the path for all services
sys.path.insert(0, str(PROJECT_ROOT / "shared"))

# Import shared libs directly
from naql_common.geo import Coordinate, find_hub  # noqa: E402, I001
from naql_common.utils import ShipmentStatus, TruckType  # noqa: E402


_loaded_services: dict[str, types.ModuleType] = {}


def _load_service_module(service_name: str, module_path: str) -> types.ModuleType:
    """Load a module from a specific service directory.

    Each service has its own `app` package. To avoid collisions we:
    1. Purge any previously-loaded `app.*` entries from sys.modules
    2. Point sys.path at the target service directory
    3. Import the requested module path normally
    4. Cache it under a service-qualified key so we can return it later
    """
    cache_key = f"{service_name}:{module_path}"
    if cache_key in _loaded_services:
        return _loaded_services[cache_key]

    service_dir = str(PROJECT_ROOT / "services" / service_name)

    # Remove any previously loaded `app` tree so the new service's app wins
    stale = [k for k in sys.modules if k == "app" or k.startswith("app.")]
    for k in stale:
        del sys.modules[k]

    # Temporarily put this service dir first on sys.path
    sys.path.insert(0, service_dir)
    try:
        mod = importlib.import_module(module_path)
    finally:
        sys.path.remove(service_dir)

    _loaded_services[cache_key] = mod
    return mod


# ══════════════════════════════════════════════════════════════
# Configuration: Egyptian Route Coordinates
# ══════════════════════════════════════════════════════════════

# Sokhna Port (Ain Sokhna) — Origin
SOKHNA_PORT = Coordinate(latitude=29.5952, longitude=32.3414)

# 6th of October City — Destination
OCTOBER_CITY = Coordinate(latitude=29.9569, longitude=30.9271)

# Intermediate waypoints (Sokhna → Ring Road → October City)
ROUTE_WAYPOINTS = [
    Coordinate(29.5952, 32.3414),  # Sokhna Port (start)
    Coordinate(29.7200, 32.0500),  # Ain Sokhna Road
    Coordinate(29.8800, 31.7500),  # Approaching Cairo Ring Road
    Coordinate(29.9800, 31.4500),  # Cairo Ring Road East
    Coordinate(30.0500, 31.2500),  # Ring Road — Autostrad
    Coordinate(30.0800, 31.1000),  # Ring Road — Mehwar
    Coordinate(30.0200, 30.9800),  # Approaching 6th October
    Coordinate(29.9569, 30.9271),  # 6th of October City (end)
]

# Simulated fleet near Sokhna Port
FLEET_NEAR_SOKHNA = [
    {
        "driver_id": f"DRV-{uuid.uuid4().hex[:8]}",
        "truck_id": f"TRK-{uuid.uuid4().hex[:8]}",
        "truck_type": TruckType.TRAILER,
        "load_capacity_kg": 30_000,
        "has_refrigeration": False,
        "latitude": 29.60 + (i * 0.005),
        "longitude": 32.34 + (i * 0.003),
        "driver_rating": 4.2 + (i * 0.15),
        "name": name,
    }
    for i, name in enumerate(
        ["Mohamed Hassan", "Ahmed Samir", "Khaled Mostafa", "Youssef Ali"]
    )
]


# ══════════════════════════════════════════════════════════════
# Logging Utility
# ══════════════════════════════════════════════════════════════


class SimulationLogger:
    """Structured logger for simulation events."""

    def __init__(self) -> None:
        self.events: list[dict] = []
        self._start_time = time.monotonic()

    def log(
        self,
        component: str,
        event_type: str,
        message: str,
        data: dict | None = None,
    ) -> None:
        elapsed = round(time.monotonic() - self._start_time, 3)
        entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "elapsed_sec": elapsed,
            "component": component,
            "event_type": event_type,
            "message": message,
            "data": data or {},
        }
        self.events.append(entry)
        icon = {
            "AGENT": "\U0001f9e0",
            "PLANNER": "\U0001f4cb",
            "MATCHING": "\U0001f69b",
            "PRICING": "\U0001f4b0",
            "FINTRACK": "\U0001f3e6",
            "TELEMETRY": "\U0001f4e1",
            "SENTINEL": "\U0001f6e1\ufe0f",
            "OPTIMIZER": "\U0001f5fa\ufe0f",
            "DISPATCHER": "\U0001f4e6",
            "SYSTEM": "\u2699\ufe0f",
            "GEOFENCE": "\U0001f4cd",
        }.get(component, "\u25b6")
        print(f"  [{elapsed:>7.3f}s] {icon} [{component}] {event_type}: {message}")
        if data:
            for k, v in data.items():
                val = json.dumps(v, default=str) if isinstance(v, (dict, list)) else str(v)
                print(f"            {k}: {val}")

    def dump_json(self, path: str) -> None:
        with open(path, "w") as f:
            json.dump(self.events, f, indent=2, default=str)


logger = SimulationLogger()


# ══════════════════════════════════════════════════════════════
# Phase 1: Fleet Registration & Client Setup
# ══════════════════════════════════════════════════════════════


def phase_1_setup():
    """Register trucks in the matching engine and set up the client."""
    matcher_mod = _load_service_module("matching-engine", "app.engine.matcher")
    GeoMatcher = matcher_mod.GeoMatcher  # noqa: N806
    TruckCandidate = matcher_mod.TruckCandidate  # noqa: N806

    print("\n" + "=" * 70)
    print("  PHASE 1: Fleet Registration & Client Setup")
    print("=" * 70)

    geo_matcher = GeoMatcher()

    logger.log(
        "SYSTEM",
        "SIMULATION_START",
        "Naql.ai Trip Simulation: Sokhna Port -> 6th October City",
        {
            "origin": "Sokhna Port (Ain Sokhna)",
            "destination": "6th of October City",
            "cargo": "30 tons of steel",
            "truck_type": "Trailer (Heavy Truck)",
        },
    )

    registered_trucks = []
    for truck_data in FLEET_NEAR_SOKHNA:
        candidate = TruckCandidate(
            driver_id=truck_data["driver_id"],
            truck_id=truck_data["truck_id"],
            truck_type=str(truck_data["truck_type"]),
            load_capacity_kg=truck_data["load_capacity_kg"],
            has_refrigeration=truck_data["has_refrigeration"],
            latitude=truck_data["latitude"],
            longitude=truck_data["longitude"],
            driver_rating=truck_data["driver_rating"],
        )
        geo_matcher.register_truck_position(candidate)
        registered_trucks.append(candidate)

        logger.log(
            "MATCHING",
            "TRUCK_REGISTERED",
            f"Registered {truck_data['name']}",
            {
                "driver_id": truck_data["driver_id"],
                "truck_id": truck_data["truck_id"],
                "truck_type": str(truck_data["truck_type"]),
                "location": f"({truck_data['latitude']:.4f}, {truck_data['longitude']:.4f})",
                "capacity_kg": truck_data["load_capacity_kg"],
                "rating": truck_data["driver_rating"],
            },
        )

    client_id = f"CLI-{uuid.uuid4().hex[:8]}"
    logger.log(
        "SYSTEM",
        "CLIENT_REGISTERED",
        f"B2B client registered: {client_id}",
        {"client_id": client_id, "company": "Egyptian Steel Industries", "region": "EG-SUE"},
    )

    return geo_matcher, registered_trucks, client_id, matcher_mod


# ══════════════════════════════════════════════════════════════
# Phase 2: AI Agent Brain — Intent Classification & Planning
# ══════════════════════════════════════════════════════════════


def phase_2_agent_brain(client_id: str):
    """Process the booking request through the AI Agent Brain."""
    brain_mod = _load_service_module("agent-orchestrator", "app.agents.naql_brain")
    Planner = brain_mod.Planner  # noqa: N806
    AgentContext = brain_mod.AgentContext  # noqa: N806
    SubTask = brain_mod.SubTask  # noqa: N806

    print("\n" + "=" * 70)
    print("  PHASE 2: AI Agent Brain -- Intent Classification & Planning")
    print("=" * 70)

    planner = Planner()

    user_message = (
        "I need to move 30 tons of steel from Sokhna Port "
        "to an industrial site in 6th of October City tomorrow morning."
    )

    logger.log("AGENT", "USER_REQUEST", f'Received: "{user_message}"', {
        "user_id": client_id,
        "language": "en",
    })

    context = AgentContext(
        session_id=str(uuid.uuid4()),
        user_id=client_id,
        user_message=user_message,
        language="en",
    )

    intent = planner.classify_intent(user_message)
    logger.log("PLANNER", "INTENT_CLASSIFIED", f"Intent: {intent}", {
        "intent": intent,
        "confidence": "high",
        "matched_keywords": ["move"],
    })

    context.intent = intent

    sub_tasks = [
        SubTask(
            id=str(uuid.uuid4()),
            description="Search for available Trailer trucks near Sokhna Port",
            tool_name="search_available_trucks",
            tool_args={
                "latitude": SOKHNA_PORT.latitude,
                "longitude": SOKHNA_PORT.longitude,
                "radius_km": 25.0,
                "truck_type": "trailer",
                "min_capacity_kg": 30000,
            },
        ),
        SubTask(
            id=str(uuid.uuid4()),
            description="Calculate price quote with Cartas (Tolls) for Sokhna -> October City",
            tool_name="get_quote",
            tool_args={
                "distance_km": round(SOKHNA_PORT.distance_km(OCTOBER_CITY), 1),
                "truck_type": "trailer",
                "weight_kg": 30000.0,
                "origin_region": "EG-SUE",
                "dest_region": "EG-CAI",
            },
        ),
        SubTask(
            id=str(uuid.uuid4()),
            description="Find optimal driver/truck match for the shipment",
            tool_name="request_match",
            tool_args={
                "shipment_id": f"SHP-{uuid.uuid4().hex[:8]}",
                "origin_lat": SOKHNA_PORT.latitude,
                "origin_lng": SOKHNA_PORT.longitude,
                "dest_lat": OCTOBER_CITY.latitude,
                "dest_lng": OCTOBER_CITY.longitude,
                "truck_type": "trailer",
                "weight_kg": 30000.0,
            },
        ),
        SubTask(
            id=str(uuid.uuid4()),
            description="Create escrow hold for shipment payment",
            tool_name="create_escrow",
            tool_args={},
        ),
    ]

    for i, task in enumerate(sub_tasks, 1):
        logger.log("PLANNER", "SUBTASK_CREATED", f"Step {i}: {task.description}", {
            "task_id": task.id[:8],
            "tool": task.tool_name,
            "args": task.tool_args,
        })

    return context, sub_tasks, brain_mod


# ══════════════════════════════════════════════════════════════
# Phase 3: Matching Engine — Find Nearest Trailer
# ══════════════════════════════════════════════════════════════


def phase_3_matching(geo_matcher, matcher_mod):
    """Execute the matching engine to find the best trailer."""
    MatchRequest = matcher_mod.MatchRequest  # noqa: N806

    print("\n" + "=" * 70)
    print("  PHASE 3: Matching Engine -- Geo-Spatial Truck Search")
    print("=" * 70)

    logger.log(
        "MATCHING",
        "SEARCH_START",
        "Searching for Trailer trucks within 25km of Sokhna Port",
        {
            "center": f"({SOKHNA_PORT.latitude}, {SOKHNA_PORT.longitude})",
            "radius_km": 25.0,
            "truck_type_filter": "trailer",
            "min_capacity_kg": 30000,
        },
    )

    candidates = geo_matcher.find_nearby_trucks(
        origin=SOKHNA_PORT,
        radius_km=25.0,
        truck_type="trailer",
        min_capacity_kg=30000,
    )

    logger.log("MATCHING", "SEARCH_COMPLETE", f"Found {len(candidates)} matching trucks", {
        "total_candidates": len(candidates),
    })

    for i, c in enumerate(candidates, 1):
        logger.log("MATCHING", "CANDIDATE", f"#{i}: Driver {c.driver_id[:12]}...", {
            "driver_id": c.driver_id,
            "truck_id": c.truck_id,
            "distance_km": c.distance_km,
            "eta_minutes": c.eta_minutes,
            "rating": c.driver_rating,
            "capacity_kg": c.load_capacity_kg,
        })

    match_request = MatchRequest(
        shipment_id=f"SHP-{uuid.uuid4().hex[:8]}",
        origin=SOKHNA_PORT,
        destination=OCTOBER_CITY,
        required_truck_type="trailer",
        weight_kg=30000.0,
        search_radius_km=25.0,
        max_candidates=5,
    )

    result = geo_matcher.match(match_request)

    logger.log(
        "MATCHING",
        "RANKED_RESULTS",
        f"Ranked {len(result.candidates)} candidates by multi-factor score",
        {"match_id": result.match_id, "total_searched": result.total_searched},
    )

    for i, c in enumerate(result.candidates, 1):
        logger.log("MATCHING", "RANKED_CANDIDATE", f"Rank #{i}: Score {c.score}", {
            "rank": i,
            "driver_id": c.driver_id,
            "score": c.score,
            "distance_km": c.distance_km,
            "eta_minutes": c.eta_minutes,
            "rating": c.driver_rating,
        })

    best = result.candidates[0] if result.candidates else None
    if best:
        logger.log(
            "MATCHING",
            "BEST_MATCH",
            f"Selected driver {best.driver_id[:12]}... (Score: {best.score})",
            {"driver_id": best.driver_id, "truck_id": best.truck_id, "score": best.score},
        )

    return result, best


# ══════════════════════════════════════════════════════════════
# Phase 4: Pricing Engine — Cartas (Tolls) Calculation
# ══════════════════════════════════════════════════════════════


def phase_4_pricing():
    """Calculate the price including Egyptian Cartas (road tolls)."""
    pricing_mod = _load_service_module("fintrack-service", "app.core.pricing")
    calculate_quote = pricing_mod.calculate_quote
    TOLL_RATES = pricing_mod.TOLL_RATES  # noqa: N806
    FUEL_RATES = pricing_mod.FUEL_RATES  # noqa: N806

    print("\n" + "=" * 70)
    print("  PHASE 4: Pricing Engine -- Cartas (Tolls) & Quote Calculation")
    print("=" * 70)

    distance_km = round(SOKHNA_PORT.distance_km(OCTOBER_CITY), 1)

    logger.log("PRICING", "DISTANCE_CALCULATED", f"Route distance: {distance_km} km (Haversine)", {
        "origin": "Sokhna Port",
        "destination": "6th of October City",
        "distance_km": distance_km,
        "note": "Actual road distance ~180-200km via Ring Road",
    })

    toll_key = ("EG-SUE", "EG-CAI")
    toll_amount = TOLL_RATES.get(toll_key, 50.0)
    logger.log(
        "PRICING",
        "CARTAS_LOOKUP",
        f"Cartas (Tolls) for {toll_key[0]} -> {toll_key[1]}: {toll_amount} EGP",
        {
            "route": f"{toll_key[0]} -> {toll_key[1]}",
            "toll_egp": toll_amount,
            "toll_gates": ["Ain Sokhna Gate", "Cairo Ring Road Gate", "6th October Axis Gate"],
            "note": "Includes Sokhna Highway + Regional Ring Road tolls",
        },
    )

    fuel_rate = FUEL_RATES[TruckType.TRAILER]
    logger.log("PRICING", "FUEL_RATE", f"Trailer fuel rate: {fuel_rate} EGP/km", {
        "truck_type": "trailer",
        "rate_egp_per_km": fuel_rate,
        "diesel_price_note": "Based on Egyptian diesel at ~10 EGP/liter",
    })

    quote = calculate_quote(
        distance_km=distance_km,
        truck_type=TruckType.TRAILER,
        weight_kg=30000.0,
        origin_region="EG-SUE",
        dest_region="EG-CAI",
    )

    logger.log("PRICING", "QUOTE_GENERATED", f"Total quote: {quote.total_egp} EGP", {
        "total_egp": quote.total_egp,
        "fuel_cost_egp": quote.fuel_cost_egp,
        "toll_cost_egp": quote.toll_cost_egp,
        "service_fee_egp": quote.service_fee_egp,
        "insurance_fee_egp": quote.insurance_fee_egp,
        "weight_surcharge": "Applied (30t > 10t threshold)",
    })

    logger.log("PRICING", "TOLL_TABLE", "Available Cartas (Toll) Routes:", {
        "routes": {f"{k[0]}->{k[1]}": f"{v} EGP" for k, v in TOLL_RATES.items()},
    })

    return quote


# ══════════════════════════════════════════════════════════════
# Phase 5: FinTrack — Escrow Transaction
# ══════════════════════════════════════════════════════════════


def phase_5_escrow(client_id: str, quote, best_match):
    """Create an escrow hold for the shipment payment."""
    print("\n" + "=" * 70)
    print("  PHASE 5: FinTrack -- Escrow Transaction")
    print("=" * 70)

    # Simulate balances in-memory (mirrors the FinTrack in-memory store logic)
    fund_amount = quote.total_egp + 5000.0
    balance = {"available_egp": fund_amount, "held_egp": 0.0, "total_egp": fund_amount}

    logger.log("FINTRACK", "WALLET_FUNDED", f"Client wallet funded with {fund_amount} EGP", {
        "client_id": client_id,
        "available_egp": balance["available_egp"],
        "total_egp": balance["total_egp"],
    })

    escrow_id = f"ESC-{uuid.uuid4().hex[:8].upper()}"
    shipment_id = f"SHP-{uuid.uuid4().hex[:8].upper()}"

    if balance["available_egp"] < quote.total_egp:
        logger.log("FINTRACK", "ESCROW_REJECTED", "Insufficient funds", {
            "required": quote.total_egp,
            "available": balance["available_egp"],
        })
        return None, None, balance

    balance["available_egp"] -= quote.total_egp
    balance["held_egp"] += quote.total_egp

    logger.log("FINTRACK", "ESCROW_CREATED", f"Escrow {escrow_id} created: {quote.total_egp} EGP held", {
        "escrow_id": escrow_id,
        "shipment_id": shipment_id,
        "payer_id": client_id,
        "amount_egp": quote.total_egp,
        "status": "held",
        "driver_id": best_match.driver_id if best_match else "N/A",
    })

    logger.log("FINTRACK", "BALANCE_AFTER_ESCROW", "Updated client balance", {
        "available_egp": round(balance["available_egp"], 2),
        "held_egp": round(balance["held_egp"], 2),
        "total_egp": round(balance["total_egp"], 2),
    })

    return escrow_id, shipment_id, balance


# ══════════════════════════════════════════════════════════════
# Phase 6: Route Optimization — OR-Tools CVRP
# ══════════════════════════════════════════════════════════════


def phase_6_route_optimization():
    """Plan the optimal route using OR-Tools CVRP solver."""
    optimizer_mod = _load_service_module("agent-orchestrator", "app.agents.route_optimizer")
    RouteOptimizer = optimizer_mod.RouteOptimizer  # noqa: N806
    Location = optimizer_mod.Location  # noqa: N806
    Vehicle = optimizer_mod.Vehicle  # noqa: N806

    print("\n" + "=" * 70)
    print("  PHASE 6: Route Optimization -- CVRP Solver")
    print("=" * 70)

    optimizer = RouteOptimizer()

    locations = [
        Location(
            id="depot",
            latitude=SOKHNA_PORT.latitude,
            longitude=SOKHNA_PORT.longitude,
            name="Sokhna Port (Depot)",
            demand_kg=0,
        ),
        Location(
            id="pickup",
            latitude=SOKHNA_PORT.latitude,
            longitude=SOKHNA_PORT.longitude,
            name="Sokhna Port -- Steel Pickup",
            demand_kg=30000,
            service_time_min=45,
        ),
        Location(
            id="ring_road_junction",
            latitude=30.05,
            longitude=31.25,
            name="Cairo Ring Road Junction",
            demand_kg=0,
            service_time_min=5,
        ),
        Location(
            id="delivery",
            latitude=OCTOBER_CITY.latitude,
            longitude=OCTOBER_CITY.longitude,
            name="6th October Industrial Zone",
            demand_kg=0,
            service_time_min=60,
        ),
    ]

    vehicles = [
        Vehicle(
            id="V1",
            capacity_kg=35000,
            max_distance_km=500,
            max_driving_hours=8.0,
            cost_per_km=7.5,
            truck_type="trailer",
        ),
    ]

    logger.log("OPTIMIZER", "SOLVING", "Running CVRP solver for Sokhna -> October City route", {
        "num_locations": len(locations),
        "num_vehicles": len(vehicles),
        "or_tools_available": optimizer._or_tools_available,
        "solver_mode": "OR-Tools CP-SAT" if optimizer._or_tools_available else "Greedy Nearest-Neighbor",
    })

    result = optimizer.optimize(locations, vehicles)

    logger.log("OPTIMIZER", "SOLUTION_FOUND", f"Route optimized ({result.solver_status})", {
        "solver_status": result.solver_status,
        "total_distance_km": result.total_distance_km,
        "total_cost_egp": result.total_cost_egp,
        "num_routes": len(result.routes),
    })

    for route in result.routes:
        logger.log("OPTIMIZER", "ROUTE_PLAN", f"Vehicle {route.vehicle.id}: {route.total_distance_km} km", {
            "vehicle_id": route.vehicle.id,
            "stops": [s.location.name for s in route.stops],
            "total_distance_km": route.total_distance_km,
            "estimated_time_min": route.total_time_min,
            "cost_egp": route.cost_egp,
            "total_load_kg": route.total_load_kg,
        })

    return result


# ══════════════════════════════════════════════════════════════
# Phase 7: Telemetry Simulation — GPS Waypoints
# ══════════════════════════════════════════════════════════════


def phase_7_telemetry(best_match, shipment_id: str):
    """Simulate GPS telemetry along the Sokhna -> October City route."""
    processor_mod = _load_service_module("telemetry-ingress", "app.processing.processor")
    MessageProcessor = processor_mod.MessageProcessor  # noqa: N806

    print("\n" + "=" * 70)
    print("  PHASE 7: Telemetry Simulation -- GPS & Sensor Data")
    print("=" * 70)

    processor = MessageProcessor()
    truck_id = best_match.truck_id if best_match else "TRK-SIM-001"
    driver_id = best_match.driver_id if best_match else "DRV-SIM-001"
    trip_id = f"TRIP-{uuid.uuid4().hex[:8]}"

    logger.log("TELEMETRY", "TRIP_STARTED", f"Trip {trip_id} started", {
        "trip_id": trip_id,
        "truck_id": truck_id,
        "driver_id": driver_id,
        "shipment_id": shipment_id,
    })

    all_events: list[dict] = []
    speeds = [0, 45, 80, 90, 100, 85, 75, 0]

    waypoint_names = [
        "Sokhna Port",
        "Ain Sokhna Road",
        "Approaching Ring Road",
        "Ring Road East",
        "Autostrad",
        "Mehwar",
        "Approaching October",
        "6th October City",
    ]

    for i, (waypoint, speed) in enumerate(zip(ROUTE_WAYPOINTS, speeds, strict=True)):
        topic = f"naql/truck/{truck_id}/position"
        payload = json.dumps({
            "truck_id": truck_id,
            "driver_id": driver_id,
            "trip_id": trip_id,
            "latitude": waypoint.latitude,
            "longitude": waypoint.longitude,
            "altitude_m": 50.0 + (i * 10),
            "speed_kmh": speed,
            "heading": 270.0 - (i * 15),
            "signal_strength": max(1, 5 - (i % 3)),
            "connection_type": "4G" if i % 2 == 0 else "3G",
            "ignition_on": True,
        }).encode("utf-8")

        pos_msg = processor.parse_position(topic, payload)
        events = processor.process_position(pos_msg)

        hub = find_hub(waypoint)
        hub_name = hub or "Open Road"

        logger.log(
            "TELEMETRY",
            "GPS_UPDATE",
            f"Waypoint {i + 1}/{len(ROUTE_WAYPOINTS)}: {waypoint_names[i]}",
            {
                "position": f"({waypoint.latitude:.4f}, {waypoint.longitude:.4f})",
                "speed_kmh": speed,
                "hub": hub_name,
                "buffer_size": processor.position_buffer_size,
            },
        )

        for event in events:
            event_type = event["type"]
            if event_type == "geofence_entered":
                logger.log("GEOFENCE", "ENTERED", f"Entered hub: {event['hub']}", event)
            elif event_type == "geofence_exited":
                logger.log("GEOFENCE", "EXITED", f"Exited hub: {event['hub']}", event)
            elif event_type == "speed_violation":
                logger.log(
                    "SENTINEL",
                    "SPEED_VIOLATION",
                    f"Speed {event['speed_kmh']} km/h exceeds limit",
                    event,
                )
            all_events.append(event)

    # Simulate OBD-II telemetry
    telemetry_topic = f"naql/truck/{truck_id}/telemetry"
    telemetry_payload = json.dumps({
        "truck_id": truck_id,
        "engine_rpm": 2200,
        "engine_temp_c": 95.0,
        "fuel_level_pct": 65.0,
        "fuel_rate_lph": 28.5,
        "odometer_km": 142350.0,
        "battery_voltage": 13.8,
        "cargo_temp_c": None,
        "harsh_braking": False,
        "harsh_acceleration": False,
        "sharp_turn": False,
    }).encode("utf-8")

    tel_msg = processor.parse_telemetry(telemetry_topic, telemetry_payload)
    tel_events = processor.process_telemetry(tel_msg)

    logger.log("TELEMETRY", "SENSOR_DATA", "OBD-II telemetry received", {
        "engine_rpm": 2200,
        "engine_temp_c": 95.0,
        "fuel_level_pct": 65.0,
        "battery_voltage": 13.8,
        "alerts": [e["type"] for e in tel_events] if tel_events else "none",
    })

    pos_batch = processor.flush_position_buffer()
    tel_batch = processor.flush_telemetry_buffer()

    logger.log(
        "TELEMETRY",
        "BUFFER_FLUSH",
        f"Flushed {len(pos_batch)} positions, {len(tel_batch)} telemetry records",
        {
            "position_records": len(pos_batch),
            "telemetry_records": len(tel_batch),
            "ready_for_timescaledb": True,
        },
    )

    return all_events, trip_id


# ══════════════════════════════════════════════════════════════
# Phase 8: Sentinel Monitoring — Anomaly Detection
# ══════════════════════════════════════════════════════════════


async def phase_8_sentinel(trip_id: str, shipment_id: str, telemetry_events: list):
    """Process events through the Sentinel real-time monitor."""
    brain_mod = _load_service_module("agent-orchestrator", "app.agents.naql_brain")
    Sentinel = brain_mod.Sentinel  # noqa: N806

    print("\n" + "=" * 70)
    print("  PHASE 8: Sentinel Monitor -- Anomaly Detection & Response")
    print("=" * 70)

    sentinel = Sentinel()
    sentinel.start_monitoring(trip_id, shipment_id)

    logger.log("SENTINEL", "MONITORING_STARTED", f"Sentinel active for trip {trip_id}", {
        "trip_id": trip_id,
        "shipment_id": shipment_id,
    })

    for event in telemetry_events:
        event_type = event.get("type", "unknown")
        result = await sentinel.process_event(event_type, event)
        if result:
            logger.log("SENTINEL", "ALERT_TRIGGERED", f"Alert: {result['reason']}", {
                "action": result["action"],
                "severity": result["severity"],
                "notify_client": result.get("notify_client", False),
            })

    # Simulate ETA deviation
    eta_result = await sentinel.process_event("eta_deviation", {
        "truck_id": "TRK-SIM-001",
        "shipment_id": shipment_id,
        "deviation_minutes": 25,
        "original_eta_minutes": 180,
        "new_eta_minutes": 205,
    })
    if eta_result:
        logger.log("SENTINEL", "ETA_DEVIATION", f"ETA deviation detected: {eta_result['reason']}", {
            "action": eta_result["action"],
            "severity": eta_result["severity"],
            "notify_client": eta_result.get("notify_client", False),
        })

    # Simulate breakdown scenario
    breakdown_result = await sentinel.process_event("truck_breakdown", {
        "truck_id": "TRK-SIM-001",
        "shipment_id": shipment_id,
        "location": "Cairo Ring Road, km 45",
        "breakdown_type": "tire_blowout",
    })
    if breakdown_result:
        logger.log("SENTINEL", "BREAKDOWN_DETECTED", f"CRITICAL: {breakdown_result['reason']}", {
            "action": breakdown_result["action"],
            "severity": breakdown_result["severity"],
            "notify_client": breakdown_result.get("notify_client", False),
            "next_step": "Automatic re-assignment triggered via NATS JetStream",
        })

    sentinel.stop_monitoring(trip_id)
    logger.log("SENTINEL", "MONITORING_STOPPED", f"Sentinel stopped for trip {trip_id}")


# ══════════════════════════════════════════════════════════════
# Phase 9: Escrow Release & Trip Completion
# ══════════════════════════════════════════════════════════════


def phase_9_completion(client_id: str, escrow_id: str, best_match, quote, balance: dict):
    """Complete the trip and release escrow funds."""
    print("\n" + "=" * 70)
    print("  PHASE 9: Trip Completion & Escrow Release")
    print("=" * 70)

    driver_id = best_match.driver_id if best_match else "DRV-SIM-001"

    # Release escrow: deduct from payer
    balance["held_egp"] -= quote.total_egp
    balance["total_egp"] -= quote.total_egp

    # Credit driver
    driver_balance = {"available_egp": quote.total_egp, "held_egp": 0.0, "total_egp": quote.total_egp}

    logger.log("FINTRACK", "ESCROW_RELEASED", f"Escrow {escrow_id} released to driver", {
        "escrow_id": escrow_id,
        "amount_egp": quote.total_egp,
        "released_to": driver_id,
        "payer_balance": {
            "available_egp": round(balance["available_egp"], 2),
            "held_egp": round(balance["held_egp"], 2),
            "total_egp": round(balance["total_egp"], 2),
        },
        "driver_balance": {
            "available_egp": round(driver_balance["available_egp"], 2),
            "total_egp": round(driver_balance["total_egp"], 2),
        },
    })

    logger.log("SYSTEM", "TRIP_COMPLETED", "Shipment delivered successfully!", {
        "status": str(ShipmentStatus.DELIVERED),
        "origin": "Sokhna Port",
        "destination": "6th of October City",
        "cargo": "30 tons of steel",
        "total_cost_egp": quote.total_egp,
    })


# ══════════════════════════════════════════════════════════════
# Main Simulation Runner
# ══════════════════════════════════════════════════════════════


async def run_simulation():
    """Execute the full end-to-end trip simulation."""
    print("\n" + "#" * 70)
    print("#" + " " * 68 + "#")
    print("#   NAQL.AI -- Autonomous Logistics Simulation                      #")
    print("#   Route: Sokhna Port  -->  6th of October City                    #")
    print("#   Cargo: 30 tons of steel | Truck: Trailer (Heavy)               #")
    print("#" + " " * 68 + "#")
    print("#" * 70)

    # Phase 1: Setup
    geo_matcher, _fleet, client_id, matcher_mod = phase_1_setup()

    # Phase 2: Agent Brain
    _context, _sub_tasks, _brain_mod = phase_2_agent_brain(client_id)

    # Phase 3: Matching
    match_result, best_match = phase_3_matching(geo_matcher, matcher_mod)

    # Phase 4: Pricing
    quote = phase_4_pricing()

    # Phase 5: Escrow
    escrow_id, shipment_id, balance = phase_5_escrow(client_id, quote, best_match)

    # Phase 6: Route Optimization
    _route_result = phase_6_route_optimization()

    # Phase 7: Telemetry
    telemetry_events, trip_id = phase_7_telemetry(best_match, shipment_id or "SHP-SIM")

    # Phase 8: Sentinel
    await phase_8_sentinel(trip_id, shipment_id or "SHP-SIM", telemetry_events)

    # Phase 9: Completion
    if escrow_id and best_match:
        phase_9_completion(client_id, escrow_id, best_match, quote, balance)

    # ── Summary ────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("  SIMULATION SUMMARY")
    print("=" * 70)

    distance = round(SOKHNA_PORT.distance_km(OCTOBER_CITY), 1)
    print(f"""
    Route:          Sokhna Port -> 6th of October City
    Distance:       {distance} km (straight-line)
    Cargo:          30 tons of steel
    Truck Type:     Trailer (Heavy Truck)
    Quote:          {quote.total_egp} EGP
      - Fuel:       {quote.fuel_cost_egp} EGP
      - Tolls:      {quote.toll_cost_egp} EGP (Cartas)
      - Service:    {quote.service_fee_egp} EGP
      - Insurance:  {quote.insurance_fee_egp} EGP
    Drivers Found:  {len(match_result.candidates)}
    Best Driver:    {best_match.driver_id[:12] if best_match else 'N/A'}... (Score: {best_match.score if best_match else 0})
    Escrow:         {escrow_id or 'N/A'}
    GPS Waypoints:  {len(ROUTE_WAYPOINTS)}
    Events:         {len(telemetry_events)} anomaly events detected
    Status:         DELIVERED
    """)

    # Save full event log
    log_path = str(PROJECT_ROOT / "scripts" / "simulation_log.json")
    logger.dump_json(log_path)
    print(f"  Full event log saved to: {log_path}")
    print(f"  Total events logged: {len(logger.events)}")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_simulation())
