"""GraphQL API Gateway for Naql.ai — Strawberry-based schema."""

from __future__ import annotations

from datetime import UTC, datetime

import strawberry

from ..services import ServiceClient

# ── Types ──────────────────────────────────────────────────


@strawberry.type
class User:
    """User account type."""

    id: str
    email: str
    phone: str
    full_name: str
    role: str
    kyc_status: str
    reputation_score: float
    region_code: str
    is_active: bool
    created_at: datetime


@strawberry.type
class LiveLocation:
    """Latest known location for a truck."""

    truck_id: str
    timestamp: datetime
    latitude: float
    longitude: float
    speed_kmh: float
    h3_index: str | None = None
    region_code: str | None = None


@strawberry.type
class AuthPayload:
    """Authentication response type."""

    user_id: str
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    role: str
    region_code: str


@strawberry.type
class Truck:
    """Truck entity type."""

    id: str
    owner_id: str
    license_plate: str
    truck_type: str
    load_capacity_kg: int
    status: str
    region_code: str
    has_refrigeration: bool
    vin: str | None = None
    make: str | None = None
    model: str | None = None


@strawberry.type
class MatchCandidate:
    """A matched driver/truck candidate."""

    driver_id: str
    truck_id: str
    truck_type: str
    score: float
    distance_km: float
    eta_minutes: int
    driver_rating: float


@strawberry.type
class MatchResult:
    """Match result from the matching engine."""

    match_id: str
    candidates: list[MatchCandidate]
    total_searched: int


@strawberry.type
class PriceQuote:
    """Price quote for a shipment."""

    quote_id: str
    total_egp: float
    fuel_cost_egp: float
    toll_cost_egp: float
    service_fee_egp: float
    insurance_fee_egp: float
    valid_until: datetime


@strawberry.type
class Balance:
    """User account balance."""

    user_id: str
    available_egp: float
    held_egp: float
    total_egp: float


@strawberry.type
class ChatResponse:
    """AI agent chat response."""

    session_id: str
    response: str
    intent: str


@strawberry.type
class Shipment:
    """Shipment entity type."""

    id: str
    reference_number: str
    client_id: str
    region_code: str
    status: str
    origin_address: str
    origin_lat: float
    origin_lng: float
    origin_h3_index: str
    dest_address: str
    dest_lat: float
    dest_lng: float
    dest_h3_index: str
    commodity_type: str
    weight_kg: float
    distance_km: float | None = None
    quoted_price_egp: float | None = None
    created_at: datetime


@strawberry.type
class TelemetryStats:
    """Real-time telemetry processing statistics."""

    position_buffer_size: int
    telemetry_buffer_size: int


# ── Inputs ─────────────────────────────────────────────────


@strawberry.input
class RegisterInput:
    """Input for user registration."""

    email: str
    phone: str
    password: str
    full_name: str
    role: str = "client_individual"
    region_code: str = "EG-CAI"
    national_id: str | None = None


@strawberry.input
class LoginInput:
    """Input for user login."""

    email: str
    password: str


@strawberry.input
class CoordinateInput:
    """Geographic coordinate input."""

    latitude: float
    longitude: float


@strawberry.input
class MatchRequestInput:
    """Input for requesting a match."""

    shipment_id: str
    origin: CoordinateInput
    destination: CoordinateInput
    required_truck_type: str | None = None
    weight_kg: float = 0.0
    requires_refrigeration: bool = False
    search_radius_km: float = 20.0


@strawberry.input
class QuoteInput:
    """Input for getting a price quote."""

    distance_km: float
    truck_type: str
    weight_kg: float
    origin_region: str
    dest_region: str
    requires_refrigeration: bool = False


@strawberry.input
class ChatInput:
    """Input for AI agent chat."""

    user_id: str
    message: str
    session_id: str | None = None
    language: str = "en"


# ── Service client singleton ──────────────────────────────

_client: ServiceClient | None = None


def get_service_client() -> ServiceClient:
    """Get or create the service client singleton."""
    global _client
    if _client is None:
        _client = ServiceClient()
    return _client


# ── Queries ────────────────────────────────────────────────


@strawberry.type
class Query:
    """Root GraphQL queries."""

    @strawberry.field
    async def me(self, info: strawberry.types.Info) -> User | None:
        """Get current authenticated user."""
        request = info.context["request"]
        auth_header = request.headers.get("authorization", "")
        if not auth_header.startswith("Bearer "):
            return None
        token = auth_header.removeprefix("Bearer ")
        client = get_service_client()
        data = client.get_me(token)
        if data is None:
            return None
        return User(
            id=data["id"],
            email=data["email"],
            phone=data["phone"],
            full_name=data["full_name"],
            role=data["role"],
            kyc_status=data["kyc_status"],
            reputation_score=data["reputation_score"],
            region_code=data["region_code"],
            is_active=data["is_active"],
            created_at=datetime.fromisoformat(str(data["created_at"])),
        )

    @strawberry.field
    async def user(self, user_id: str) -> User | None:
        """Get a user by ID."""
        client = get_service_client()
        data = client.get_user(user_id)
        if data is None:
            return None
        return User(
            id=data["id"],
            email=data["email"],
            phone=data["phone"],
            full_name=data["full_name"],
            role=data["role"],
            kyc_status=data["kyc_status"],
            reputation_score=data["reputation_score"],
            region_code=data["region_code"],
            is_active=data["is_active"],
            created_at=datetime.fromisoformat(str(data["created_at"])),
        )

    @strawberry.field
    async def truck(self, truck_id: str) -> Truck | None:
        """Get a truck by ID."""
        client = get_service_client()
        data = client.get_truck(truck_id)
        if data is None:
            return None
        return Truck(
            id=data["id"],
            owner_id=data["owner_id"],
            license_plate=data["license_plate"],
            truck_type=data["truck_type"],
            load_capacity_kg=data["load_capacity_kg"],
            status=data["status"],
            region_code=data["region_code"],
            has_refrigeration=data.get("has_refrigeration", False),
            vin=data.get("vin"),
            make=data.get("make"),
            model=data.get("model"),
        )

    @strawberry.field
    async def trucks(
        self,
        page: int = 1,
        page_size: int = 20,
        truck_type: str | None = None,
        region_code: str | None = None,
    ) -> list[Truck]:
        """List trucks with filtering."""
        client = get_service_client()
        items = client.list_trucks(
            page=page, page_size=page_size, truck_type=truck_type, region_code=region_code
        )
        return [
            Truck(
                id=t["id"],
                owner_id=t["owner_id"],
                license_plate=t["license_plate"],
                truck_type=t["truck_type"],
                load_capacity_kg=t["load_capacity_kg"],
                status=t["status"],
                region_code=t["region_code"],
                has_refrigeration=t.get("has_refrigeration", False),
                vin=t.get("vin"),
                make=t.get("make"),
                model=t.get("model"),
            )
            for t in items
        ]

    @strawberry.field
    async def shipment(self, shipment_id: str) -> Shipment | None:
        """Get a shipment by ID."""
        client = get_service_client()
        data = client.get_shipment(shipment_id)
        if data is None:
            return None
        return Shipment(
            id=data["id"],
            reference_number=data["reference_number"],
            client_id=data.get("client_id", ""),
            region_code=data.get("region_code", ""),
            status=data["status"],
            origin_address=data["origin_address"],
            origin_lat=data.get("origin_lat", 0.0),
            origin_lng=data.get("origin_lng", 0.0),
            origin_h3_index=data.get("origin_h3_index", ""),
            dest_address=data["dest_address"],
            dest_lat=data.get("dest_lat", 0.0),
            dest_lng=data.get("dest_lng", 0.0),
            dest_h3_index=data.get("dest_h3_index", ""),
            commodity_type=data["commodity_type"],
            weight_kg=data["weight_kg"],
            distance_km=data.get("distance_km"),
            quoted_price_egp=data.get("quoted_price_egp"),
            created_at=datetime.fromisoformat(str(data.get("created_at", datetime.now(UTC).isoformat()))),
        )

    @strawberry.field
    async def shipments(
        self,
        client_id: str | None = None,
        status: str | None = None,
    ) -> list[Shipment]:
        """List shipments with filtering."""
        client = get_service_client()
        items = client.list_shipments(client_id=client_id, status=status)
        return [
            Shipment(
                id=s["id"],
                reference_number=s["reference_number"],
                client_id=s.get("client_id", ""),
                region_code=s.get("region_code", ""),
                status=s["status"],
                origin_address=s["origin_address"],
                origin_lat=s.get("origin_lat", 0.0),
                origin_lng=s.get("origin_lng", 0.0),
                origin_h3_index=s.get("origin_h3_index", ""),
                dest_address=s["dest_address"],
                dest_lat=s.get("dest_lat", 0.0),
                dest_lng=s.get("dest_lng", 0.0),
                dest_h3_index=s.get("dest_h3_index", ""),
                commodity_type=s["commodity_type"],
                weight_kg=s["weight_kg"],
                distance_km=s.get("distance_km"),
                quoted_price_egp=s.get("quoted_price_egp"),
                created_at=datetime.fromisoformat(str(s.get("created_at", datetime.now(UTC).isoformat()))),
            )
            for s in items
        ]

    @strawberry.field
    async def get_live_location(self, truck_id: str) -> LiveLocation | None:
        """Get the latest known location for a truck."""
        client = get_service_client()
        data = client.get_latest_positions(truck_id, limit=1)
        positions = data.get("positions", []) if isinstance(data, dict) else []
        if not positions:
            return None
        p0 = positions[0]
        return LiveLocation(
            truck_id=data.get("truck_id", truck_id),
            timestamp=datetime.fromisoformat(str(p0["timestamp"])),
            latitude=float(p0["latitude"]),
            longitude=float(p0["longitude"]),
            speed_kmh=float(p0.get("speed", 0.0) or 0.0),
            h3_index=p0.get("h3_index"),
            region_code=p0.get("region_code"),
        )

    @strawberry.field
    async def balance(self, user_id: str) -> Balance | None:
        """Get user account balance."""
        client = get_service_client()
        data = client.get_balance(user_id)
        if data is None:
            return None
        return Balance(
            user_id=data.get("user_id", user_id),
            available_egp=data["available_egp"],
            held_egp=data["held_egp"],
            total_egp=data["total_egp"],
        )

    @strawberry.field
    async def telemetry_stats(self) -> TelemetryStats:
        """Get real-time telemetry processing stats."""
        return TelemetryStats(position_buffer_size=0, telemetry_buffer_size=0)


# ── Mutations ──────────────────────────────────────────────


@strawberry.type
class Mutation:
    """Root GraphQL mutations."""

    @strawberry.mutation
    async def register(self, input: RegisterInput) -> AuthPayload:
        """Register a new user via Identity Service."""
        client = get_service_client()
        data = client.register({
            "email": input.email,
            "phone": input.phone,
            "password": input.password,
            "full_name": input.full_name,
            "role": input.role,
            "region_code": input.region_code,
            "national_id": input.national_id,
        })
        return AuthPayload(
            user_id=data["user_id"],
            access_token=data["access_token"],
            refresh_token=data["refresh_token"],
            role=data["role"],
            region_code=data["region_code"],
        )

    @strawberry.mutation
    async def login(self, input: LoginInput) -> AuthPayload:
        """Login via Identity Service."""
        client = get_service_client()
        data = client.login(input.email, input.password)
        return AuthPayload(
            user_id=data["user_id"],
            access_token=data["access_token"],
            refresh_token=data["refresh_token"],
            role=data["role"],
            region_code=data["region_code"],
        )

    @strawberry.mutation
    async def request_match(self, input: MatchRequestInput) -> MatchResult:
        """Request a truck/driver match via Matching Engine."""
        client = get_service_client()
        data = client.request_match({
            "shipment_id": input.shipment_id,
            "origin": {"latitude": input.origin.latitude, "longitude": input.origin.longitude},
            "destination": {"latitude": input.destination.latitude, "longitude": input.destination.longitude},
            "required_truck_type": input.required_truck_type,
            "weight_kg": input.weight_kg,
            "requires_refrigeration": input.requires_refrigeration,
            "search_radius_km": input.search_radius_km,
        })
        candidates = [
            MatchCandidate(
                driver_id=c["driver_id"],
                truck_id=c["truck_id"],
                truck_type=c["truck_type"],
                score=c["score"],
                distance_km=c["distance_km"],
                eta_minutes=c["eta_minutes"],
                driver_rating=c["driver_rating"],
            )
            for c in data.get("candidates", [])
        ]
        return MatchResult(
            match_id=data.get("match_id", ""),
            candidates=candidates,
            total_searched=data.get("total_searched", 0),
        )

    @strawberry.mutation
    async def get_quote(self, input: QuoteInput) -> PriceQuote:
        """Get a price quote via FinTrack Service."""
        client = get_service_client()
        data = client.get_quote({
            "distance_km": input.distance_km,
            "truck_type": input.truck_type,
            "weight_kg": input.weight_kg,
            "origin_region": input.origin_region,
            "dest_region": input.dest_region,
            "requires_refrigeration": input.requires_refrigeration,
        })
        return PriceQuote(
            quote_id=data.get("quote_id", ""),
            total_egp=data["total_egp"],
            fuel_cost_egp=data.get("fuel_cost_egp", 0.0),
            toll_cost_egp=data.get("toll_cost_egp", 0.0),
            service_fee_egp=data.get("service_fee_egp", 0.0),
            insurance_fee_egp=data.get("insurance_fee_egp", 0.0),
            valid_until=datetime.fromisoformat(str(data["valid_until"]))
            if "valid_until" in data
            else datetime.now(UTC),
        )

    @strawberry.mutation
    async def chat(self, input: ChatInput) -> ChatResponse:
        """Send a message to the Naql.ai AI agent."""
        client = get_service_client()
        data = client.chat({
            "user_id": input.user_id,
            "message": input.message,
            "session_id": input.session_id,
            "language": input.language,
        })
        return ChatResponse(
            session_id=data.get("session_id", ""),
            response=data.get("response", ""),
            intent=data.get("intent", "general"),
        )


# ── Schema ─────────────────────────────────────────────────

schema = strawberry.Schema(query=Query, mutation=Mutation)
