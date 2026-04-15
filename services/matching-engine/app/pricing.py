"""Simple pricing calculation for shipments."""

import math


def calculate_shipment_price(
    origin_lat: float,
    origin_lng: float,
    dest_lat: float,
    dest_lng: float,
    weight_kg: float,
    requires_refrigeration: bool = False,
) -> float:
    """Calculate shipment price using simplified Egyptian pricing logic.

    Uses haversine distance and applies:
    - Base rate per km
    - Weight factor
    - Refrigeration surcharge
    - Service fee
    """
    # Calculate distance using haversine formula
    R = 6371  # Earth's radius in km

    lat1_rad = math.radians(origin_lat)
    lat2_rad = math.radians(dest_lat)
    delta_lat = math.radians(dest_lat - origin_lat)
    delta_lng = math.radians(dest_lng - origin_lng)

    a = math.sin(delta_lat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lng / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance_km = R * c

    # Base rate: 3 EGP per km
    base_rate = 3.0
    fuel_cost = distance_km * base_rate

    # Weight factor: extra cost for heavy loads
    if weight_kg > 5000:
        weight_factor = 1.0 + (weight_kg - 5000) / 10000
    else:
        weight_factor = 1.0
    fuel_cost *= weight_factor

    # Refrigeration surcharge
    if requires_refrigeration:
        fuel_cost *= 1.3

    # Toll cost (simplified)
    toll_cost = distance_km * 0.5

    # Insurance
    insurance = distance_km * 0.2

    # Subtotal
    subtotal = fuel_cost + toll_cost + insurance

    # Service fee (8%)
    service_fee = subtotal * 0.08

    total = subtotal + service_fee

    return round(total, 2)
