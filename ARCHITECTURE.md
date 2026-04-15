# Naql.ai — System Architecture (2025)

> Next-generation autonomous logistics ecosystem for Egypt.
> Real-time fleet tracking, AI-driven dispatching, and automated pricing.

---

## 1. High-Level Overview

Naql.ai is an **Event-Driven Microservices Architecture (EDMA)** designed for
nation-scale reliability across Egypt. The system uses regional cell sharding
to minimize latency and isolate failures between high-density urban centers
(Cairo, Alexandria) and long-haul desert highway corridors.

```
┌─────────────────────────────────────────────────────────────────┐
│                     CLIENT LAYER                                │
│  Next.js 16 + Tailwind + Mapbox GL  │  Driver Mobile App (RN)  │
└───────────────────┬─────────────────┴───────────────────────────┘
                    │ GraphQL / WebSocket
┌───────────────────▼─────────────────────────────────────────────┐
│               GRAPHQL GATEWAY (Strawberry + FastAPI)            │
│  Port 4000  │  Federation  │  Auth Header Forwarding            │
└───┬───────┬────────┬────────┬───────────┬───────────────────────┘
    │       │        │        │           │
    ▼       ▼        ▼        ▼           ▼
┌───────┐┌───────┐┌────────┐┌─────────┐┌──────────────────────┐
│Identity││Fleet  ││Match   ││FinTrack ││ Agent Orchestrator   │
│Service ││Service││Engine  ││Service  ││ (Naql Brain)         │
│:8001   ││:8002  ││:8003   ││:8004    ││ :8005                │
└───┬────┘└───┬───┘└───┬────┘└────┬────┘└──────┬───────────────┘
    │         │        │          │             │
    ▼         ▼        ▼          ▼             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      DATA LAYER                                 │
│  CockroachDB (SQL)  │  TimescaleDB (Time-Series)  │  Redis     │
│  NATS JetStream     │  EMQX (MQTT)                │  Pinecone  │
└─────────────────────────────────────────────────────────────────┘
                    ▲
┌───────────────────┴─────────────────────────────────────────────┐
│            TELEMETRY INGRESS SERVICE (:8006)                    │
│  MQTT → Batch Writer → TimescaleDB Hypertables                 │
│  Real-time: Redis GEO  │  Geofence Detection  │  Violations    │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Technology Stack

| Layer              | Technology                          | Purpose                                    |
|--------------------|-------------------------------------|--------------------------------------------|
| **Frontend**       | Next.js 16, React 19, Tailwind v4   | SSR dashboard, God View admin panel        |
| **Map Engine**     | Mapbox GL JS                        | Real-time fleet visualization              |
| **API Gateway**    | Strawberry GraphQL + FastAPI        | Unified external API with federation       |
| **Microservices**  | FastAPI (Python 3.12+)              | Domain services with async I/O             |
| **AI Agent**       | LangGraph + OR-Tools                | Agentic workflow, constraint optimization  |
| **Vector Memory**  | Pinecone                            | RAG-based long-term agent memory           |
| **Transactional DB** | CockroachDB                      | Distributed SQL (users, orders, billing)   |
| **Time-Series DB** | TimescaleDB                        | GPS history, OBD-II sensor data            |
| **Cache/Geo**      | Redis Stack                         | Geospatial index, session cache            |
| **Event Bus**      | NATS JetStream                      | Async event streaming between services     |
| **IoT Ingress**    | EMQX (MQTT)                         | Low-bandwidth truck telemetry              |
| **Auth**           | JWT (HS256) + RBAC                  | Role-based access with regional scoping    |
| **ORM**            | SQLAlchemy 2.0 (async)              | Database abstraction with dependency injection |
| **Containerization** | Docker Compose                    | Local development orchestration            |
| **Infrastructure** | Terraform + AWS EKS (planned)       | Production Kubernetes deployment           |

---

## 3. Service Architecture

### 3.1 Identity Service (`:8001`)

**Purpose:** Authentication, authorization, and user lifecycle management.

- JWT-based auth with access + refresh tokens
- RBAC with 4 roles: `client_individual`, `client_enterprise`, `driver`, `admin`
- Permission-based access control (USERS_READ, USERS_WRITE, FLEET_*, etc.)
- KYC verification workflow
- Phone + email uniqueness enforcement
- Self-registration restricted to non-admin roles

### 3.2 Fleet Service (`:8002`)

**Purpose:** Truck lifecycle management and asset tracking.

- Truck registration with Egyptian truck categories:
  `quarter_load`, `half_load`, `full_load`, `jumbo`, `trailer`,
  `refrigerated`, `tanker`, `flatbed`
- Status management: `offline` → `available` → `en_route` → `loading`
- Regional assignment (EG-CAI, EG-ALX, EG-SOK, etc.)
- Maintenance log tracking

### 3.3 Matching Engine (`:8003`)

**Purpose:** Geospatial driver/truck assignment.

- H3 hexagonal spatial indexing for O(1) proximity queries
- Multi-factor scoring: distance (40%), rating (25%), ETA (20%), price (15%)
- Google OR-Tools CVRP solver with greedy fallback
- Configurable search radius (default 20km)
- Real-time position updates via Redis GEO

### 3.4 FinTrack Service (`:8004`)

**Purpose:** Financial ledger, pricing, and payment processing.

- **Pricing Engine** with Egyptian-specific logic:
  - Fuel cost: distance × consumption rate × fuel price × weight factor
  - **Cartas (Tolls):** 28+ route corridors with truck-type multipliers
  - Service fee: 7.5% of subtotal
  - Insurance: 5% of fuel cost
- **Escrow System:** Hold → Release/Refund lifecycle
- **Balance Management:** Available, held, and total tracking
- Payment gateway stubs: Fawry, Paymob, Valu, bank transfer

#### Toll Route Coverage

| Corridor | Base Toll (EGP) | Coverage |
|----------|---------------:|----------|
| Cairo ↔ Alexandria | 180 | Desert Road (3 gates) |
| Cairo ↔ Suez | 120 | Cairo-Suez Road (2 gates) |
| Sokhna Port ↔ Cairo | 140 | Ain Sokhna Road + Ring Road |
| Sokhna ↔ 6th October | 120 | Regional Ring Road (3 gates) |
| Sokhna ↔ 10th Ramadan | 100 | Via Suez Road (2 gates) |
| Cairo ↔ 6th October | 60 | Rod El Farag Axis |
| Cairo ↔ 10th Ramadan | 75 | Cairo-Ismailia Road |
| Port Said ↔ Cairo | 170 | International Coastal Road |
| Damietta ↔ Cairo | 160 | Damietta-Mansoura Highway |

**Truck-Type Multipliers:** Quarter (0.5×), Half (0.7×), Full (1.0×),
Jumbo (1.3×), Trailer (1.5×), Refrigerated (1.2×), Tanker (1.4×), Flatbed (1.3×)

### 3.5 Agent Orchestrator — "Naql Brain" (`:8005`)

**Purpose:** LLM-driven cognitive layer for logistics automation.

- **LangGraph StateGraph:** `classify → plan → execute → respond`
- **Intent Classification:** Arabic + English NLP
  - Supported intents: `request_shipment`, `check_status`, `get_quote`,
    `track_truck`, `check_balance`, `general_question`
- **Planner:** Decomposes requests into sub-tasks
- **Dispatcher:** OR-Tools CVRP solver wrapping the Matching Engine
- **Sentinel:** Real-time event monitor
  - Breakdown detection → automatic re-assignment
  - ETA deviation alerts → route recalculation
  - Geofence violations → compliance notifications
  - Speed violations → safety alerts
- **Long-Term Memory:** Pinecone vector store for user preferences and RAG

### 3.6 Telemetry Ingress (`:8006`)

**Purpose:** High-frequency IoT data pipeline.

- MQTT message parsing (position + OBD-II telemetry)
- Batch buffering for efficient TimescaleDB writes
- **Geofence Detection:** 8 Egyptian logistics hubs with entry/exit events
  - Hub-to-hub transitions emit both exit and entry events
- **Violation Detection:**
  - Speed > 120 km/h → speed violation event
  - Engine temp > 110°C → critical overheat alert
  - Harsh braking/acceleration/turns → driving behavior events
- Regional derivation from GPS coordinates (H3-based)

---

## 4. Data Architecture

### 4.1 CockroachDB (Transactional)

```sql
-- Core tables (partitioned by region)
users          -- Auth, KYC, reputation scores
trucks         -- Fleet registry with telemetry IDs
shipments      -- Versioned state machine with audit trail
trips          -- Active route tracking
payments       -- Ledger entries
escrow_holds   -- Multi-party fund holds
```

### 4.2 TimescaleDB (Time-Series)

```sql
-- Hypertables with continuous aggregates
truck_positions      -- GPS: lat, lng, speed, heading (1s intervals)
truck_telemetry      -- OBD-II: RPM, temp, fuel, battery (5s intervals)
geofence_events      -- Hub entry/exit events
driving_violations   -- Speed, harsh braking, overheat alerts

-- Continuous aggregates
hourly_position_summary   -- Avg speed, distance per truck per hour
daily_fuel_consumption    -- Daily fuel metrics per truck
```

### 4.3 Redis Stack

- **GEO index:** Real-time truck positions for proximity queries
- **Session cache:** JWT token blacklisting
- **Rate limiting:** API throttling per client tier

---

## 5. Frontend Architecture

### Technology

- **Next.js 16** (App Router) with React 19 Server Components
- **Tailwind CSS v4** for utility-first styling
- **Mapbox GL JS** for real-time fleet visualization

### Pages

| Route | Purpose |
|-------|---------|
| `/` | Landing page |
| `/dashboard` | God View — live fleet map + KPIs |
| `/dashboard/fleet` | Fleet management table |
| `/dashboard/shipments` | Shipment tracking |
| `/dashboard/analytics` | Route performance metrics |

### Real-Time Map Component

The `LiveMap` component renders:
- Truck markers with status-based coloring (green/blue/amber/gray)
- Geofence overlay circles for 8 Egyptian logistics hubs
- Popup cards with truck ID, speed, and status
- 3-second position refresh cycle (WebSocket in production)

---

## 6. Security

- **JWT tokens** with HMAC-SHA256 signing (32+ byte keys in production)
- **RBAC** with granular permissions per role
- **Self-registration** restricted to non-admin roles (422 on admin/ops)
- **Phone/email uniqueness** enforced at registration
- **Profile authorization** — users can only edit their own profiles
- **No secrets in code** — all credentials via `.env` files (`.env.example` provided)
- **bcrypt** password hashing (direct library, not passlib wrapper)

---

## 7. Testing

### Integration Test Suite

17 tests covering the full lifecycle:

| Service | Tests | Coverage |
|---------|------:|----------|
| Identity | 5 | Registration, duplicates, login, role restriction |
| FinTrack | 3 | Pricing quotes, escrow lifecycle, insufficient funds |
| Telemetry | 5 | GPS ingestion, geofence, speed violations, engine alerts |
| Fleet | 2 | Truck registration, status updates |
| Matching | 1 | Health check |
| Cross-service | 1 | Full lifecycle pricing validation |

```bash
# Run all integration tests
python -m pytest tests/integration/test_full_cycle.py -v

# Lint check
ruff check services/ gateway/ tests/
```

### Simulation Script

```bash
# Full Sokhna → 6th October simulation with AI agent decisions
python scripts/simulate_trip.py
```

Simulates: Agent classification → Matching → Pricing → Escrow → GPS tracking →
Geofence events → Sentinel alerts → Delivery completion.

---

## 8. Deployment

### Local Development

```bash
# Start all infrastructure
docker-compose up -d

# Install Python dependencies
pip install -e shared/
pip install -e services/identity-service/
# ... (repeat for each service)

# Start frontend
cd frontend && npm install && npm run dev

# Run services
uvicorn app.main:app --port 8001  # Identity
uvicorn app.main:app --port 8002  # Fleet
# ... etc
```

### Production (Planned)

- **AWS EKS** (me-central-1) with Blue/Green deployments
- **Terraform** for infrastructure as code
- **NATS JetStream** for cross-region event replication
- **Edge Processing** for offline telemetry reconciliation

---

## 9. Regional Cell Architecture

```
┌──────────────────────────────────────────────┐
│              EGYPT CELL MAP                  │
│                                              │
│   EG-ALX ●─────────────────● EG-DKH         │
│           │    Delta        │                │
│           │                 │                │
│   EG-OCT ●── EG-CAI ──● EG-RAM              │
│           │  (Primary)      │                │
│           │                 │                │
│           │                 ● EG-SUE         │
│           │                 │                │
│   EG-FYM ●                 ● EG-SOK         │
│           │                                  │
│   EG-UEG ●  (Upper Egypt)                   │
└──────────────────────────────────────────────┘
```

Each cell operates independently with local Redis caches and can be
promoted to a primary if the Cairo cell fails. Cross-cell communication
uses NATS JetStream for eventual consistency.

---

## 10. API Contracts

### GraphQL Gateway (`:4000`)

**Mutations:**
- `register(input: RegisterInput!): AuthPayload!`
- `login(input: LoginInput!): AuthPayload!`
- `requestMatch(input: MatchRequestInput!): MatchResult!`
- `getQuote(input: QuoteInput!): PriceQuote!`
- `chat(input: ChatInput!): ChatResponse!`

**Queries:**
- `me: User` (requires Bearer token)
- `user(userId: String!): User`
- `truck(truckId: String!): Truck`
- `trucks(page: Int, pageSize: Int, truckType: String, regionCode: String): [Truck!]!`
- `balance(userId: String!): Balance`
- `telemetryStats: TelemetryStats!`

### Internal REST APIs

| Service | Endpoint | Method | Purpose |
|---------|----------|--------|---------|
| Identity | `/api/v1/auth/register` | POST | User registration |
| Identity | `/api/v1/auth/login` | POST | Authentication |
| Fleet | `/api/v1/trucks` | POST | Register truck |
| Fleet | `/api/v1/trucks/{id}/status` | PATCH | Update status |
| FinTrack | `/api/v1/quotes` | POST | Get price quote |
| FinTrack | `/api/v1/escrow` | POST | Create escrow hold |
| FinTrack | `/api/v1/escrow/release` | POST | Release escrow |
| Telemetry | `/api/v1/ingest/position` | POST | GPS data |
| Telemetry | `/api/v1/ingest/telemetry` | POST | OBD-II data |
| Agent | `/api/v1/agent/chat` | POST | AI conversation |

---

*Document generated for Naql.ai stakeholder review.*
*Architecture version: 0.1.0 | Last updated: 2025*
