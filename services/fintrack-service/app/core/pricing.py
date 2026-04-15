"""Pricing engine for Egyptian logistics - handles quotes, tolls, and fuel calculations.

Egyptian "Cartas" (road tolls) are calculated per-route based on the major
highway corridors. Rates reflect 2024/2025 toll gate pricing for heavy vehicles
on expressways managed by the Egyptian National Roads Authority.

2025 Calibration Notes:
- Diesel price: ~12.50 EGP/L (post-subsidy reform)
- Average truck consumption: 35-55 L/100km depending on type
- Toll rates updated per Egyptian National Roads Authority 2024/2025 tariffs
- Target: Sokhna→October (142 km, 30-ton Trailer) ≈ 4,500-6,500 EGP
"""

from __future__ import annotations

from dataclasses import dataclass

from naql_common.utils import TruckType

from .config import settings


@dataclass
class PriceBreakdown:
    """Detailed price breakdown for a shipment quote."""

    fuel_cost_egp: float
    toll_cost_egp: float
    service_fee_egp: float
    insurance_fee_egp: float
    total_egp: float


# ── Egyptian Toll Gates ("Cartas") ─────────────────────────────────────
#
# Toll rates for major Egyptian highway corridors.
# Key: (origin_region, dest_region) → total tolls in EGP for heavy trucks.
# Rates updated to 2024/2025 Egyptian National Roads Authority tariffs.
#
# Major corridors covered:
#   - Cairo-Alexandria Desert Road  (طريق الصحراوي)
#   - Cairo-Ain Sokhna Road         (طريق العين السخنة)
#   - Cairo Ring Road               (الطريق الدائري)
#   - Rod El Farag Axis             (محور روض الفرج)
#   - Cairo-Ismailia Road           (طريق الإسماعيلية)
#   - Cairo-Suez Road               (طريق السويس)
#   - Regional Ring Road            (الطريق الإقليمي)
#   - Upper Egypt Highway           (طريق الصعيد)

TOLL_RATES: dict[tuple[str, str], float] = {
    # Cairo ↔ Alexandria (Desert Road - 3 toll gates)
    ("EG-CAI", "EG-ALX"): 450.0,
    ("EG-ALX", "EG-CAI"): 450.0,
    # Cairo ↔ Suez (Cairo-Suez Road - 2 toll gates)
    ("EG-CAI", "EG-SUE"): 300.0,
    ("EG-SUE", "EG-CAI"): 300.0,
    # Cairo ↔ Delta (Agricultural Road - 1 toll gate)
    ("EG-CAI", "EG-DLT"): 180.0,
    ("EG-DLT", "EG-CAI"): 180.0,
    # Cairo ↔ Upper Egypt (Upper Egypt Highway - multiple toll gates)
    ("EG-CAI", "EG-UEG"): 550.0,
    ("EG-UEG", "EG-CAI"): 550.0,
    # Alexandria ↔ Delta (International Coastal Road)
    ("EG-ALX", "EG-DLT"): 150.0,
    ("EG-DLT", "EG-ALX"): 150.0,
    # Suez ↔ Sinai (Ahmed Hamdi Tunnel)
    ("EG-SUE", "EG-SIN"): 400.0,
    ("EG-SIN", "EG-SUE"): 400.0,
    # ── Sokhna corridor (critical for container traffic) ──
    # Sokhna Port ↔ Cairo (via Ain Sokhna Road - 2 toll gates + Ring Road)
    ("EG-SOK", "EG-CAI"): 350.0,
    ("EG-CAI", "EG-SOK"): 350.0,
    # Sokhna Port ↔ 6th October (via Regional Ring Road - 3 toll gates)
    ("EG-SOK", "EG-OCT"): 320.0,
    ("EG-OCT", "EG-SOK"): 320.0,
    # Sokhna Port ↔ 10th Ramadan (via Suez Road - 2 toll gates)
    ("EG-SOK", "EG-RAM"): 250.0,
    ("EG-RAM", "EG-SOK"): 250.0,
    # ── Rod El Farag Axis & Ring Road corridors ──
    # Cairo ↔ 6th October (via Rod El Farag Axis / Mehwar - 1 toll gate)
    ("EG-CAI", "EG-OCT"): 150.0,
    ("EG-OCT", "EG-CAI"): 150.0,
    # Cairo ↔ 10th Ramadan (via Cairo-Ismailia Road - 1 toll gate)
    ("EG-CAI", "EG-RAM"): 180.0,
    ("EG-RAM", "EG-CAI"): 180.0,
    # ── Industrial zone corridors ──
    # 6th October ↔ Alexandria (via Desert Road - 2 toll gates)
    ("EG-OCT", "EG-ALX"): 380.0,
    ("EG-ALX", "EG-OCT"): 380.0,
    # 10th Ramadan ↔ Suez (via Ismailia Road - 1 toll gate)
    ("EG-RAM", "EG-SUE"): 220.0,
    ("EG-SUE", "EG-RAM"): 220.0,
    # ── Port corridors ──
    # Damietta ↔ Cairo (via International Coastal → Delta Road)
    ("EG-DAM", "EG-CAI"): 420.0,
    ("EG-CAI", "EG-DAM"): 420.0,
    # Port Said ↔ Cairo (via Ismailia Road)
    ("EG-PSD", "EG-CAI"): 440.0,
    ("EG-CAI", "EG-PSD"): 440.0,
    # Damietta ↔ 10th Ramadan
    ("EG-DAM", "EG-RAM"): 320.0,
    ("EG-RAM", "EG-DAM"): 320.0,
    # ── Cross-regional ──
    # 6th October ↔ Upper Egypt (via Fayoum Road)
    ("EG-OCT", "EG-UEG"): 480.0,
    ("EG-UEG", "EG-OCT"): 480.0,
    # Suez ↔ Ismailia
    ("EG-SUE", "EG-ISM"): 180.0,
    ("EG-ISM", "EG-SUE"): 180.0,
    # Alexandria ↔ Damietta (via International Coastal Road)
    ("EG-ALX", "EG-DAM"): 300.0,
    ("EG-DAM", "EG-ALX"): 300.0,
}

# ── Heavy vehicle surcharge multipliers ────────────────────────────────
# Egyptian toll gates charge more for heavier vehicles.
TOLL_TRUCK_MULTIPLIERS: dict[TruckType, float] = {
    TruckType.QUARTER_LOAD: 0.5,
    TruckType.HALF_LOAD: 0.7,
    TruckType.FULL_LOAD: 1.0,
    TruckType.JUMBO: 1.3,
    TruckType.TRAILER: 1.5,
    TruckType.REFRIGERATED: 1.2,
    TruckType.TANKER: 1.4,
    TruckType.FLATBED: 1.3,
}

# Fuel rates per km by truck type (EGP/km, based on 2025 diesel prices ~12.50 EGP/L)
# Calculated from: consumption (L/100km) x diesel price (EGP/L) / 100
# Example: Trailer = 50 L/100km x 12.50 EGP/L / 100 = 6.25 -> rounded up for wear
FUEL_RATES: dict[TruckType, float] = {
    TruckType.QUARTER_LOAD: 8.0,    # ~25 L/100km light pickup
    TruckType.HALF_LOAD: 10.5,      # ~32 L/100km medium truck
    TruckType.FULL_LOAD: 14.0,      # ~40 L/100km standard hauler
    TruckType.JUMBO: 18.0,          # ~48 L/100km heavy truck
    TruckType.TRAILER: 22.0,        # ~55 L/100km heavy trailer + wear
    TruckType.REFRIGERATED: 24.0,   # ~55 L/100km + reefer unit power draw
    TruckType.TANKER: 20.0,         # ~52 L/100km liquid cargo
    TruckType.FLATBED: 19.0,        # ~50 L/100km open-bed heavy
}


def calculate_quote(
    distance_km: float,
    truck_type: TruckType,
    weight_kg: float,
    origin_region: str,
    dest_region: str,
    requires_refrigeration: bool = False,
) -> PriceBreakdown:
    """Calculate a detailed price quote for a shipment.

    Uses configurable rates from settings (FINTRACK_* env vars) with fallback
    to the truck-type-specific FUEL_RATES table.

    Factors:
    - Fuel cost: Based on distance x truck type fuel rate
    - Toll cost: Based on route (origin/dest regions) with truck-type multiplier
    - Service fee: configurable % of subtotal (default 8%)
    - Insurance: configurable per-km rate
    - Weight surcharge: Applied for heavy loads > 10 tons
    """
    # Fuel cost — use truck-specific rate with settings fallback
    fuel_rate = FUEL_RATES.get(truck_type, settings.BASE_FUEL_RATE_PER_KM)
    if requires_refrigeration and truck_type != TruckType.REFRIGERATED:
        fuel_rate *= 1.3  # 30% surcharge for cooling

    fuel_cost = distance_km * fuel_rate

    # Weight surcharge for loads > 10 tons
    if weight_kg > 10000:
        weight_factor = 1.0 + (weight_kg - 10000) / 50000
        fuel_cost *= weight_factor

    # Toll cost - base rate from route table, adjusted by truck type multiplier
    base_toll = TOLL_RATES.get((origin_region, dest_region), 120.0)
    truck_multiplier = TOLL_TRUCK_MULTIPLIERS.get(truck_type, 1.0)
    toll_cost = base_toll * truck_multiplier

    # Insurance — from settings
    insurance_fee = distance_km * settings.INSURANCE_RATE_PER_KM

    # Subtotal before service fee
    subtotal = fuel_cost + toll_cost + insurance_fee

    # Service fee — from settings
    service_fee = subtotal * settings.SERVICE_FEE_PERCENTAGE

    # Total
    total = subtotal + service_fee

    return PriceBreakdown(
        fuel_cost_egp=round(fuel_cost, 2),
        toll_cost_egp=round(toll_cost, 2),
        service_fee_egp=round(service_fee, 2),
        insurance_fee_egp=round(insurance_fee, 2),
        total_egp=round(total, 2),
    )
