"""Geo-spatial matching engine — the core dispatch algorithm.

Uses Redis geospatial indexes + H3 hexagonal grid for efficient
nearby truck lookups, combined with a multi-factor scoring system.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field

from naql_common.geo import Coordinate, get_h3_ring


@dataclass
class TruckCandidate:
    """A candidate truck/driver for matching."""

    driver_id: str
    truck_id: str
    truck_type: str
    load_capacity_kg: int
    has_refrigeration: bool
    latitude: float
    longitude: float
    driver_rating: float
    distance_km: float = 0.0
    eta_minutes: int = 0
    score: float = 0.0


@dataclass
class MatchRequest:
    """Request parameters for finding a match."""

    shipment_id: str
    origin: Coordinate
    destination: Coordinate
    required_truck_type: str | None = None
    weight_kg: float = 0.0
    requires_refrigeration: bool = False
    search_radius_km: float = 20.0
    max_candidates: int = 10


@dataclass
class MatchResult:
    """Result of the matching process."""

    match_id: str
    candidates: list[TruckCandidate] = field(default_factory=list)
    total_searched: int = 0


class ScoringEngine:
    """Multi-factor scoring engine for ranking truck candidates.

    Scoring factors:
    - Distance: Closer trucks score higher (inverse distance)
    - Rating: Higher driver ratings score higher
    - ETA: Faster arrival scores higher
    - Price efficiency: Better price/km ratio scores higher

    Weights are configurable per deployment region.
    """

    def __init__(
        self,
        weight_distance: float = 0.30,
        weight_rating: float = 0.25,
        weight_eta: float = 0.25,
        weight_price: float = 0.20,
    ) -> None:
        self.weight_distance = weight_distance
        self.weight_rating = weight_rating
        self.weight_eta = weight_eta
        self.weight_price = weight_price

    def score_candidate(
        self,
        candidate: TruckCandidate,
        max_distance_km: float,
        max_eta_minutes: int,
    ) -> float:
        """Calculate a normalized score (0.0 - 1.0) for a candidate."""
        # Distance score: inverse normalized (closer = better)
        if max_distance_km > 0:
            distance_score = 1.0 - (candidate.distance_km / max_distance_km)
        else:
            distance_score = 1.0

        # Rating score: normalized to 0-1 (rating is 1.0 - 5.0)
        rating_score = (candidate.driver_rating - 1.0) / 4.0

        # ETA score: inverse normalized (faster = better)
        eta_score = 1.0 - (candidate.eta_minutes / max_eta_minutes) if max_eta_minutes > 0 else 1.0

        # Price score: for now, use capacity utilization as proxy
        price_score = 0.7  # Default baseline

        # Weighted sum
        total = (
            self.weight_distance * distance_score
            + self.weight_rating * rating_score
            + self.weight_eta * eta_score
            + self.weight_price * price_score
        )

        return round(min(1.0, max(0.0, total)), 3)

    def rank_candidates(
        self,
        candidates: list[TruckCandidate],
        max_results: int = 10,
    ) -> list[TruckCandidate]:
        """Score and rank all candidates, returning top N."""
        if not candidates:
            return []

        max_distance = max(c.distance_km for c in candidates) if candidates else 1.0
        max_eta = max(c.eta_minutes for c in candidates) if candidates else 1

        for candidate in candidates:
            candidate.score = self.score_candidate(candidate, max_distance, max_eta)

        # Sort by score descending
        candidates.sort(key=lambda c: c.score, reverse=True)

        return candidates[:max_results]


class GeoMatcher:
    """Performs geo-spatial matching using H3 hexagonal grid.

    This is the in-memory component. In production, this interfaces
    with Redis GEO commands for real-time truck position lookups.
    """

    def __init__(self) -> None:
        self._scoring_engine = ScoringEngine()
        # In-memory truck positions (replace with Redis in production)
        self._truck_positions: dict[str, TruckCandidate] = {}

    def register_truck_position(self, candidate: TruckCandidate) -> None:
        """Register or update a truck's position."""
        self._truck_positions[candidate.truck_id] = candidate

    def remove_truck(self, truck_id: str) -> None:
        """Remove a truck from the available pool."""
        self._truck_positions.pop(truck_id, None)

    def find_nearby_trucks(
        self,
        origin: Coordinate,
        radius_km: float = 20.0,
        truck_type: str | None = None,
        min_capacity_kg: int = 0,
        requires_refrigeration: bool = False,
    ) -> list[TruckCandidate]:
        """Find available trucks within radius using H3 grid search."""
        # Get H3 hexagons in search radius
        search_hexes = set(get_h3_ring(origin, radius_km))

        candidates: list[TruckCandidate] = []

        for truck in self._truck_positions.values():
            truck_coord = Coordinate(truck.latitude, truck.longitude)
            truck_hex = truck_coord.to_h3()

            # Check if truck is in search area
            if truck_hex not in search_hexes:
                continue

            # Apply filters
            if truck_type and truck.truck_type != truck_type:
                continue
            if truck.load_capacity_kg < min_capacity_kg:
                continue
            if requires_refrigeration and not truck.has_refrigeration:
                continue

            # Calculate actual distance
            distance = origin.distance_km(truck_coord)
            if distance > radius_km:
                continue

            # Create a copy to avoid mutating the shared position index
            avg_speed = 50.0  # Blended average for Egypt
            matched = dataclasses.replace(
                truck,
                distance_km=round(distance, 2),
                eta_minutes=max(1, int((distance / avg_speed) * 60)),
            )

            candidates.append(matched)

        return candidates

    def match(self, request: MatchRequest) -> MatchResult:
        """Execute a full match: find nearby trucks, score, and rank."""
        import uuid

        candidates = self.find_nearby_trucks(
            origin=request.origin,
            radius_km=request.search_radius_km,
            truck_type=request.required_truck_type,
            min_capacity_kg=int(request.weight_kg),
            requires_refrigeration=request.requires_refrigeration,
        )

        total_searched = len(candidates)
        ranked = self._scoring_engine.rank_candidates(
            candidates, max_results=request.max_candidates
        )

        return MatchResult(
            match_id=str(uuid.uuid4()),
            candidates=ranked,
            total_searched=total_searched,
        )
