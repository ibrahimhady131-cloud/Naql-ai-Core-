"""Geospatial utilities for H3 indexing, distance calculations, and geofencing."""

from __future__ import annotations

import math
from dataclasses import dataclass

import h3


@dataclass(frozen=True)
class Coordinate:
    """A geographic coordinate (WGS84)."""

    latitude: float
    longitude: float

    def to_h3(self, resolution: int = 9) -> str:
        """Convert to H3 hex index at given resolution.

        Resolution guide:
            - 5: ~252 km² (governorate level)
            - 7: ~5.16 km² (district level)
            - 9: ~0.105 km² (neighborhood level) — default
            - 11: ~0.00165 km² (street level)
        """
        return h3.latlng_to_cell(self.latitude, self.longitude, resolution)

    def distance_km(self, other: Coordinate) -> float:
        """Calculate Haversine distance in kilometers."""
        r = 6371.0  # Earth's radius in km

        lat1, lon1 = math.radians(self.latitude), math.radians(self.longitude)
        lat2, lon2 = math.radians(other.latitude), math.radians(other.longitude)

        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return r * c


@dataclass(frozen=True)
class BoundingBox:
    """A geographic bounding box."""

    min_lat: float
    min_lng: float
    max_lat: float
    max_lng: float

    def contains(self, coord: Coordinate) -> bool:
        """Check if a coordinate is within the bounding box."""
        return (
            self.min_lat <= coord.latitude <= self.max_lat
            and self.min_lng <= coord.longitude <= self.max_lng
        )


# Egyptian logistics hub geofences
EGYPT_HUBS: dict[str, BoundingBox] = {
    "sokhna_port": BoundingBox(29.55, 32.30, 29.65, 32.40),
    "damietta_port": BoundingBox(31.40, 31.75, 31.50, 31.85),
    "alexandria_port": BoundingBox(31.17, 29.85, 31.22, 29.95),
    "10th_ramadan": BoundingBox(30.25, 31.70, 30.40, 31.85),
    "6th_october": BoundingBox(29.90, 30.85, 30.05, 31.05),
    "cairo_ring_road": BoundingBox(29.95, 31.10, 30.15, 31.45),
    "suez_canal_zone": BoundingBox(30.40, 32.25, 31.30, 32.60),
    "sadat_city": BoundingBox(30.30, 30.45, 30.45, 30.55),
}


def get_h3_ring(center: Coordinate, radius_km: float, resolution: int = 9) -> list[str]:
    """Get H3 hexagons in a ring around a center point.

    Used for nearby truck search.
    """
    center_h3 = center.to_h3(resolution)
    # Approximate ring size: each hex at res 9 is ~350m edge length
    edge_length_km = h3.average_hexagon_edge_length(resolution, unit="km")
    k = max(1, int(radius_km / edge_length_km))
    return list(h3.grid_disk(center_h3, k))


def find_hub(coord: Coordinate) -> str | None:
    """Find which Egyptian logistics hub a coordinate falls within."""
    for hub_name, bbox in EGYPT_HUBS.items():
        if bbox.contains(coord):
            return hub_name
    return None


# Egyptian governorate → region cell mapping
REGION_CELLS: dict[str, str] = {
    "cairo": "EG-CAI",
    "giza": "EG-CAI",
    "qalyubia": "EG-CAI",
    "alexandria": "EG-ALX",
    "beheira": "EG-ALX",
    "matrouh": "EG-ALX",
    "suez": "EG-SUE",
    "ismailia": "EG-SUE",
    "port_said": "EG-SUE",
    "red_sea": "EG-SUE",
    "sharqia": "EG-DLT",
    "dakahlia": "EG-DLT",
    "damietta": "EG-DLT",
    "kafr_el_sheikh": "EG-DLT",
    "gharbia": "EG-DLT",
    "monufia": "EG-DLT",
    "minya": "EG-UEG",
    "asyut": "EG-UEG",
    "sohag": "EG-UEG",
    "qena": "EG-UEG",
    "luxor": "EG-UEG",
    "aswan": "EG-UEG",
    "fayoum": "EG-UEG",
    "beni_suef": "EG-UEG",
    "north_sinai": "EG-SIN",
    "south_sinai": "EG-SIN",
    "new_valley": "EG-WST",
}
