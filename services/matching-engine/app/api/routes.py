"""Matching Engine API routes."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, select

from naql_common.db.deps import CockroachSession
from naql_common.db.models.shipment import Shipment
from naql_common.geo import Coordinate

from ..engine.matcher import GeoMatcher, MatchRequest, TruckCandidate
from ..schemas.matching import (
    AvailableTrucksRequestSchema,
    MatchCandidateSchema,
    MatchDecisionSchema,
    MatchRequestSchema,
    MatchResponseSchema,
    ShipmentCreateSchema,
    ShipmentResponseSchema,
    TruckLocationUpdateSchema,
)

router = APIRouter(prefix="/api/v1", tags=["matching"])

# Global matcher instance
geo_matcher = GeoMatcher()

# Track match decisions
_match_decisions: dict[str, dict] = {}


@router.post("/match", response_model=MatchResponseSchema)
async def request_match(request: MatchRequestSchema) -> MatchResponseSchema:
    """Find optimal truck/driver matches for a shipment."""
    match_req = MatchRequest(
        shipment_id=request.shipment_id,
        origin=Coordinate(request.origin.latitude, request.origin.longitude),
        destination=Coordinate(request.destination.latitude, request.destination.longitude),
        required_truck_type=request.required_truck_type,
        weight_kg=request.weight_kg,
        requires_refrigeration=request.requires_refrigeration,
        search_radius_km=request.search_radius_km,
        max_candidates=request.max_candidates,
    )

    result = geo_matcher.match(match_req)

    return MatchResponseSchema(
        match_id=result.match_id,
        candidates=[
            MatchCandidateSchema(
                driver_id=c.driver_id,
                truck_id=c.truck_id,
                truck_type=c.truck_type,
                score=c.score,
                distance_km=c.distance_km,
                eta_minutes=c.eta_minutes,
                driver_rating=c.driver_rating,
            )
            for c in result.candidates
        ],
        total_searched=result.total_searched,
    )


@router.post("/match/available-trucks")
async def get_available_trucks(request: AvailableTrucksRequestSchema) -> dict:
    """Query available trucks in a geographic area."""
    origin = Coordinate(request.center.latitude, request.center.longitude)

    candidates = geo_matcher.find_nearby_trucks(
        origin=origin,
        radius_km=request.radius_km,
        truck_type=request.truck_type,
        min_capacity_kg=request.min_capacity_kg,
    )

    return {
        "trucks": [
            {
                "driver_id": c.driver_id,
                "truck_id": c.truck_id,
                "truck_type": c.truck_type,
                "distance_km": c.distance_km,
                "eta_minutes": c.eta_minutes,
                "driver_rating": c.driver_rating,
            }
            for c in candidates
        ],
        "total": len(candidates),
    }


@router.post("/match/decision")
async def respond_to_match(request: MatchDecisionSchema) -> dict:
    """Record a driver's response to a match offer."""
    _match_decisions[request.match_id] = {
        "driver_id": request.driver_id,
        "decision": request.decision,
    }

    return {
        "success": True,
        "message": f"Match {request.decision} by driver {request.driver_id}",
    }


@router.post("/trucks/location")
async def update_truck_location(request: TruckLocationUpdateSchema) -> dict:
    """Update a truck's real-time position in the geo-index."""
    # Fetch truck details from Fleet Service via gRPC
    from ..grpc_client import get_fleet_client

    fleet_client = get_fleet_client()
    truck_response = await fleet_client.get_truck_details(request.truck_id)

    if truck_response:
        truck_type = truck_response.truck_type
        load_capacity_kg = truck_response.load_capacity_kg
        has_refrigeration = truck_response.has_refrigeration
        print(f"[Matching Engine] Fetched truck details via gRPC: type={truck_type}, capacity={load_capacity_kg}kg")
    else:
        # Fallback if gRPC fails
        truck_type = "unknown"
        load_capacity_kg = 0
        has_refrigeration = False
        print(f"[Matching Engine] gRPC call failed, using fallback values")

    candidate = TruckCandidate(
        driver_id=request.driver_id,
        truck_id=request.truck_id,
        truck_type=truck_type,
        load_capacity_kg=load_capacity_kg,
        has_refrigeration=has_refrigeration,
        latitude=request.latitude,
        longitude=request.longitude,
        driver_rating=4.5,  # Would be fetched from identity service
    )

    geo_matcher.register_truck_position(candidate)
    coord = Coordinate(request.latitude, request.longitude)

    return {
        "received": True,
        "h3_index": coord.to_h3(),
    }


@router.post("/shipments", response_model=ShipmentResponseSchema, status_code=status.HTTP_201_CREATED)
async def create_shipment(
    request: ShipmentCreateSchema,
    session: CockroachSession,
) -> ShipmentResponseSchema:
    """Create a new shipment."""
    # Verify shipper via Identity Service gRPC
    from ..grpc_identity_client import get_identity_client

    identity_client = get_identity_client()
    is_valid, message = await identity_client.verify_shipper(request.client_id)
    if not is_valid:
        print(f"[Matching Engine] Shipper verification failed: {message}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=message)
    print(f"[Matching Engine] Shipper verified via gRPC: {request.client_id}")

    # Generate reference number
    ref_number = f"SHP-{uuid.uuid4().hex[:8].upper()}"

    # Compute H3 indices for origin and destination
    origin_coord = Coordinate(request.origin_lat, request.origin_lng)
    dest_coord = Coordinate(request.dest_lat, request.dest_lng)

    # Parse pickup windows
    pickup_start = datetime.fromisoformat(request.pickup_window_start.replace("Z", "+00:00"))
    pickup_end = datetime.fromisoformat(request.pickup_window_end.replace("Z", "+00:00"))

    shipment = Shipment(
        reference_number=ref_number,
        client_id=uuid.UUID(request.client_id),
        region_code=request.region_code,
        origin_address=request.origin_address,
        origin_lat=request.origin_lat,
        origin_lng=request.origin_lng,
        origin_h3_index=origin_coord.to_h3(),
        dest_address=request.dest_address,
        dest_lat=request.dest_lat,
        dest_lng=request.dest_lng,
        dest_h3_index=dest_coord.to_h3(),
        commodity_type=request.commodity_type,
        weight_kg=request.weight_kg,
        volume_cbm=request.volume_cbm,
        requires_refrigeration=request.requires_refrigeration,
        pickup_window_start=pickup_start,
        pickup_window_end=pickup_end,
        quoted_price_egp=request.quoted_price_egp,
        status="pending",
    )

    session.add(shipment)
    await session.commit()
    await session.refresh(shipment)

    # Create invoice via FinTrack gRPC
    from ..grpc_fintrack_client import get_fintrack_client
    from ..pricing import calculate_shipment_price

    # Calculate price
    price = calculate_shipment_price(
        origin_lat=request.origin_lat,
        origin_lng=request.origin_lng,
        dest_lat=request.dest_lat,
        dest_lng=request.dest_lng,
        weight_kg=request.weight_kg,
        requires_refrigeration=request.requires_refrigeration,
    )

    # Call FinTrack to create invoice
    fintrack_client = get_fintrack_client()
    invoice_response = await fintrack_client.create_invoice(
        shipment_id=str(shipment.id),
        shipper_id=request.client_id,
        amount=price,
        currency="EGP",
    )

    if invoice_response:
        print(f"[Matching Engine] Invoice created via gRPC: {invoice_response.invoice_id}")
    else:
        print(f"[Matching Engine] Warning: Failed to create invoice via gRPC")

    # Publish shipment.created event to NATS
    try:
        from naql_common.events import publish_shipment_created
        await publish_shipment_created(
            shipment_id=str(shipment.id),
            pickup_h3=shipment.origin_h3_index,
            dropoff_h3=shipment.dest_h3_index,
            cargo_type=shipment.commodity_type,
        )
    except Exception as e:
        print(f"[Matching Engine] Warning: Failed to publish NATS event: {e}")

    return ShipmentResponseSchema(
        id=str(shipment.id),
        reference_number=shipment.reference_number,
        client_id=str(shipment.client_id),
        region_code=shipment.region_code,
        origin_address=shipment.origin_address,
        origin_lat=float(shipment.origin_lat),
        origin_lng=float(shipment.origin_lng),
        origin_h3_index=shipment.origin_h3_index,
        dest_address=shipment.dest_address,
        dest_lat=float(shipment.dest_lat),
        dest_lng=float(shipment.dest_lng),
        dest_h3_index=shipment.dest_h3_index,
        commodity_type=shipment.commodity_type,
        weight_kg=float(shipment.weight_kg),
        volume_cbm=float(shipment.volume_cbm) if shipment.volume_cbm else None,
        requires_refrigeration=shipment.requires_refrigeration,
        status=shipment.status,
        quoted_price_egp=float(shipment.quoted_price_egp) if shipment.quoted_price_egp else None,
        created_at=shipment.created_at.isoformat() if shipment.created_at else "",
    )


@router.get("/shipments", response_model=list[ShipmentResponseSchema])
async def list_shipments(
    session: CockroachSession,
    client_id: str | None = None,
    status: str | None = None,
    limit: int = 50,
) -> list[ShipmentResponseSchema]:
    stmt = select(Shipment)
    if client_id:
        stmt = stmt.where(Shipment.client_id == uuid.UUID(client_id))
    if status:
        stmt = stmt.where(Shipment.status == status)
    stmt = stmt.order_by(desc(Shipment.created_at)).limit(limit)
    rows = (await session.execute(stmt)).scalars().all()
    return [
        ShipmentResponseSchema(
            id=str(s.id),
            reference_number=s.reference_number,
            client_id=str(s.client_id),
            region_code=s.region_code,
            origin_address=s.origin_address,
            origin_lat=float(s.origin_lat),
            origin_lng=float(s.origin_lng),
            origin_h3_index=s.origin_h3_index,
            dest_address=s.dest_address,
            dest_lat=float(s.dest_lat),
            dest_lng=float(s.dest_lng),
            dest_h3_index=s.dest_h3_index,
            commodity_type=s.commodity_type,
            weight_kg=float(s.weight_kg),
            volume_cbm=float(s.volume_cbm) if s.volume_cbm else None,
            requires_refrigeration=s.requires_refrigeration,
            status=s.status,
            quoted_price_egp=float(s.quoted_price_egp) if s.quoted_price_egp else None,
            created_at=s.created_at.isoformat() if s.created_at else "",
        )
        for s in rows
    ]


@router.get("/shipments/{shipment_id}", response_model=ShipmentResponseSchema)
async def get_shipment(
    shipment_id: str,
    session: CockroachSession,
) -> ShipmentResponseSchema:
    """Get a shipment by ID."""
    result = await session.execute(
        select(Shipment).where(Shipment.id == uuid.UUID(shipment_id))
    )
    shipment = result.scalar_one_or_none()

    if not shipment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shipment not found")

    return ShipmentResponseSchema(
        id=str(shipment.id),
        reference_number=shipment.reference_number,
        client_id=str(shipment.client_id),
        region_code=shipment.region_code,
        origin_address=shipment.origin_address,
        origin_lat=float(shipment.origin_lat),
        origin_lng=float(shipment.origin_lng),
        origin_h3_index=shipment.origin_h3_index,
        dest_address=shipment.dest_address,
        dest_lat=float(shipment.dest_lat),
        dest_lng=float(shipment.dest_lng),
        dest_h3_index=shipment.dest_h3_index,
        commodity_type=shipment.commodity_type,
        weight_kg=float(shipment.weight_kg),
        volume_cbm=float(shipment.volume_cbm) if shipment.volume_cbm else None,
        requires_refrigeration=shipment.requires_refrigeration,
        status=shipment.status,
        quoted_price_egp=float(shipment.quoted_price_egp) if shipment.quoted_price_egp else None,
        created_at=shipment.created_at.isoformat() if shipment.created_at else "",
    )
