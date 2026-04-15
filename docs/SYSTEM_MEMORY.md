# System Memory

## Database Schema

### Identity Service Tables

#### users
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PRIMARY KEY |
| email | VARCHAR(255) | NOT NULL, UNIQUE |
| phone | VARCHAR(20) | NOT NULL, UNIQUE |
| password_hash | VARCHAR(255) | NOT NULL |
| full_name | VARCHAR(255) | NOT NULL |
| role | VARCHAR(50) | NOT NULL, DEFAULT 'client_individual' |
| kyc_status | VARCHAR(20) | NOT NULL, DEFAULT 'pending' |
| reputation_score | DECIMAL(3,2) | NOT NULL, DEFAULT 5.0 |
| region_code | VARCHAR(20) | REGIONAL MIXIN |
| national_id | VARCHAR(14) | NULLABLE, UNIQUE |
| profile_image_url | TEXT | NULLABLE |
| is_active | BOOLEAN | NOT NULL, DEFAULT true |
| last_login_at | TIMESTAMP WITH TZ | NULLABLE |
| created_at | TIMESTAMP | TIMESTAMP MIXIN |
| updated_at | TIMESTAMP | TIMESTAMP MIXIN |
| deleted_at | TIMESTAMP | SOFT DELETE MIXIN |

#### api_keys
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PRIMARY KEY |
| user_id | UUID | NOT NULL, FOREIGN KEY -> users.id |
| key_hash | VARCHAR(255) | NOT NULL, UNIQUE |
| name | VARCHAR(100) | NOT NULL |
| permissions | JSONB | NOT NULL |
| expires_at | TIMESTAMP WITH TZ | NULLABLE |
| last_used_at | TIMESTAMP WITH TZ | NULLABLE |
| created_at | TIMESTAMP | TIMESTAMP MIXIN |

#### user_documents
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PRIMARY KEY |
| user_id | UUID | NOT NULL, FOREIGN KEY -> users.id |
| document_type | VARCHAR(50) | NOT NULL |
| document_url | TEXT | NOT NULL |
| verification_status | VARCHAR(20) | NOT NULL, DEFAULT 'pending' |
| verified_at | TIMESTAMP WITH TZ | NULLABLE |
| created_at | TIMESTAMP | TIMESTAMP MIXIN |

---

### Matching Service Tables

#### shipments
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PRIMARY KEY |
| reference_number | VARCHAR(20) | NOT NULL, UNIQUE |
| client_id | UUID | NOT NULL, INDEXED |
| region_code | VARCHAR(20) | REGIONAL MIXIN |
| origin_address | VARCHAR(500) | NOT NULL |
| origin_lat | NUMERIC(10,7) | NOT NULL |
| origin_lng | NUMERIC(10,7) | NOT NULL |
| origin_h3_index | VARCHAR(15) | NOT NULL, INDEXED |
| origin_hub | VARCHAR(50) | NULLABLE |
| dest_address | VARCHAR(500) | NOT NULL |
| dest_lat | NUMERIC(10,7) | NOT NULL |
| dest_lng | NUMERIC(10,7) | NOT NULL |
| dest_h3_index | VARCHAR(15) | NOT NULL, INDEXED |
| dest_hub | VARCHAR(50) | NULLABLE |
| commodity_type | VARCHAR(100) | NOT NULL |
| description | VARCHAR(1000) | NULLABLE |
| weight_kg | NUMERIC(10,2) | NOT NULL |
| volume_cbm | NUMERIC(8,2) | NULLABLE |
| requires_refrigeration | BOOLEAN | NOT NULL, DEFAULT false |
| is_hazardous | BOOLEAN | NOT NULL, DEFAULT false |
| required_truck_type | VARCHAR(20) | NULLABLE |
| pickup_window_start | TIMESTAMP WITH TZ | NOT NULL |
| pickup_window_end | TIMESTAMP WITH TZ | NOT NULL |
| delivery_deadline | TIMESTAMP WITH TZ | NULLABLE |
| quoted_price_egp | NUMERIC(12,2) | NULLABLE |
| fuel_cost_egp | NUMERIC(10,2) | NULLABLE |
| toll_cost_egp | NUMERIC(10,2) | NULLABLE |
| status | VARCHAR(30) | NOT NULL, DEFAULT 'pending', INDEXED |
| status_history | JSONB | NOT NULL, DEFAULT [] |
| distance_km | NUMERIC(8,2) | NULLABLE |
| estimated_duration_min | INTEGER | NULLABLE |
| notes | VARCHAR(2000) | NULLABLE |
| created_at | TIMESTAMP | TIMESTAMP MIXIN |
| updated_at | TIMESTAMP | TIMESTAMP MIXIN |

---

### Fleet Service Tables

#### trucks
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PRIMARY KEY |
| owner_id | UUID | NOT NULL |
| vin | VARCHAR(17) | UNIQUE |
| license_plate | VARCHAR(20) | NOT NULL, UNIQUE |
| truck_type | VARCHAR(20) | NOT NULL, INDEXED |
| make | VARCHAR(50) | NULLABLE |
| model | VARCHAR(50) | NULLABLE |
| year | INTEGER | NULLABLE |
| load_capacity_kg | INTEGER | NOT NULL |
| has_refrigeration | BOOLEAN | NOT NULL, DEFAULT false |
| has_gps_tracker | BOOLEAN | NOT NULL, DEFAULT true |
| telemetry_device_id | VARCHAR(100) | NULLABLE |
| insurance_expiry | TIMESTAMP WITH TZ | NULLABLE |
| license_expiry | TIMESTAMP WITH TZ | NULLABLE |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'offline', INDEXED |
| region_code | VARCHAR(20) | REGIONAL MIXIN |
| created_at | TIMESTAMP | TIMESTAMP MIXIN |
| updated_at | TIMESTAMP | TIMESTAMP MIXIN |
| deleted_at | TIMESTAMP | SOFT DELETE MIXIN |

#### truck_maintenance
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PRIMARY KEY |
| truck_id | UUID | NOT NULL, FOREIGN KEY -> trucks.id, INDEXED |
| maintenance_type | VARCHAR(50) | NOT NULL |
| description | VARCHAR(1000) | NULLABLE |
| cost_egp | NUMERIC(12,2) | NULLABLE |
| odometer_km | INTEGER | NULLABLE |
| performed_at | TIMESTAMP WITH TZ | NOT NULL |
| next_due_at | TIMESTAMP WITH TZ | NULLABLE, INDEXED |
| performed_by | VARCHAR(255) | NULLABLE |
| created_at | TIMESTAMP WITH TZ | NOT NULL, DEFAULT now() |

---

## Ports and Endpoints

### Identity Service
- **Port**: 8001
- **Base URL**: http://127.0.0.1:8001
- **API Prefix**: /api/v1

#### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/v1/auth/register | Register new user |
| POST | /api/v1/auth/login | User login |
| GET | /api/v1/users/me | Get current user profile |
| GET | /api/v1/users/{user_id} | Get user by ID (requires permission) |
| PATCH | /api/v1/users/{user_id} | Update user profile |
| POST | /api/v1/users/{user_id}/kyc | Verify KYC status |
| GET | /api/v1/users | List users (paginated) |

#### Example: Register User
```bash
POST /api/v1/auth/register
Content-Type: application/json

{
  "email": "testuser@example.com",
  "phone": "+201234567890",
  "password": "SecurePass123",
  "full_name": "Test User",
  "role": "client_individual",
  "region_code": "EG-CAI",
  "national_id": "12345678901234"
}
```

#### Example: Get Current User
```bash
GET /api/v1/users/me
Authorization: Bearer <access_token>
```

---

### Matching Engine
- **Port**: 8003
- **Base URL**: http://127.0.0.1:8003
- **API Prefix**: /api/v1

#### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/v1/shipments | Create new shipment |
| GET | /api/v1/shipments/{shipment_id} | Get shipment by ID |
| POST | /api/v1/match | Find optimal truck/driver matches |
| POST | /api/v1/match/available-trucks | Query available trucks in geo area |
| POST | /api/v1/match/decision | Record driver's response to match |
| POST | /api/v1/trucks/location | Update truck real-time position |

#### Example: Create Shipment
```bash
POST /api/v1/shipments
Content-Type: application/json

{
  "client_id": "8c620951-33a8-4ef5-a282-9fba8cd8cbf4",
  "region_code": "EG-CAI",
  "origin_address": "Cairo, Egypt",
  "origin_lat": 30.0444,
  "origin_lng": 31.2357,
  "dest_address": "Alexandria, Egypt",
  "dest_lat": 31.2001,
  "dest_lng": 29.9187,
  "commodity_type": "electronics",
  "weight_kg": 500,
  "volume_cbm": 2.5,
  "requires_refrigeration": false,
  "pickup_window_start": "2026-04-16T08:00:00Z",
  "pickup_window_end": "2026-04-16T12:00:00Z",
  "quoted_price_egp": 2500
}
```

#### Example: Get Shipment
```bash
GET /api/v1/shipments/dcf0a32d-09cf-43b7-80fc-27b6f38ae6fd
```

---

### Fleet Service
- **Port**: 8002
- **Base URL**: http://127.0.0.1:8002
- **API Prefix**: /api/v1

#### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/v1/trucks | Register new truck |
| GET | /api/v1/trucks | List trucks (paginated) |
| GET | /api/v1/trucks/{truck_id} | Get truck by ID |
| PATCH | /api/v1/trucks/{truck_id} | Update truck status |
| GET | /api/v1/trucks/owner/{owner_id} | Get trucks by owner |
| POST | /api/v1/trucks/{truck_id}/maintenance | Add maintenance record |

#### Example: Create Truck
```bash
POST /api/v1/trucks
Content-Type: application/json

{
  "owner_id": "00000000-0000-0000-0000-000000000001",
  "license_plate": "ABC-124",
  "truck_type": "flatbed",
  "load_capacity_kg": 10000,
  "region_code": "EG-CAI"
}
```

#### Example: Get Truck
```bash
GET /api/v1/trucks/1af055fa-58d9-4624-9ccf-e800580d1f11
```

---

## Configuration

### Environment Variables
| Variable | Description | Example |
|----------|-------------|---------|
| DATABASE_URL | PostgreSQL connection string | postgresql+asyncpg://postgres.[ref]:[pass]@aws-0-eu-west-1.pooler.supabase.com:5432/postgres?sslmode=require |
| NAQL_SSL_CA_FILE | Path to corporate CA certificate | F:\Projects-app\BIG-DEV\prod-ca-2021.crt |
| PYTHONPATH | Module search path | f:\Projects-app\BIG-DEV;f:\Projects-app\BIG-DEV\shared |

### Supabase Connection
- **Pooler Host**: aws-0-eu-west-1.pooler.supabase.com
- **Port**: 5432
- **Database**: postgres
- **Project Ref**: zxnmsjveiymibuuooxwv

---

## Persistence Verification

### Fleet Service Test
1. Started Fleet Service with DATABASE_URL pointing to Supabase pooler
2. POST /api/v1/trucks with valid payload
3. Stopped service (process kill)
4. Restarted service with same DATABASE_URL
5. GET /api/v1/trucks/{id} - returned same data

### Result: VERIFIED
Truck persisted across service restarts using Supabase PostgreSQL database.

### Identity Service Test
1. Started Identity Service with DATABASE_URL pointing to Supabase pooler
2. POST /api/v1/auth/register with valid payload
3. Stopped service (process kill)
4. Restarted service with same DATABASE_URL
5. GET /api/v1/users/me with access token - returned same user data

### Result: VERIFIED
User persisted across service restarts using Supabase PostgreSQL database.

### Matching Engine Test
1. Started Matching Engine with DATABASE_URL pointing to Supabase pooler
2. POST /api/v1/shipments with valid payload including H3 indices
3. Stopped service (process kill)
4. Restarted service with same DATABASE_URL
5. GET /api/v1/shipments/{id} - returned same data with all location and cargo details intact

### Result: VERIFIED
Shipment persisted across service restarts using Supabase PostgreSQL database. H3 spatial indices computed correctly (origin: 893e628e67bffff, dest: 893f5ba66b3fffff).

---

## FinTrack Database Schema

### FinTrack Service Tables

#### invoices
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PRIMARY KEY |
| shipment_id | UUID | NOT NULL |
| total_amount_egp | NUMERIC(14,2) | NOT NULL |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'unpaid', INDEXED |
| created_at | TIMESTAMP | TIMESTAMP MIXIN |
| updated_at | TIMESTAMP | TIMESTAMP MIXIN |

#### ledger_entries
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PRIMARY KEY |
| account_id | UUID | NOT NULL, INDEXED |
| transaction_type | VARCHAR(10) | NOT NULL (credit/debit) |
| amount_egp | NUMERIC(14,2) | NOT NULL |
| description | VARCHAR(500) | NULLABLE |
| created_at | TIMESTAMP WITH TZ | NOT NULL, DEFAULT now() |

---

## FinTrack Ports and Endpoints

### FinTrack Service
- **Port**: 8004
- **Base URL**: http://127.0.0.1:8004
- **API Prefix**: /api/v1

#### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/v1/invoices | Create invoice |
| GET | /api/v1/invoices/{invoice_id} | Get invoice by ID |

---

## FinTrack Persistence Verification

### Test Performed
1. Started FinTrack Service with DATABASE_URL pointing to Supabase pooler
2. POST /api/v1/invoices with shipment_id=dcf0a32d-09cf-43b7-80fc-27b6f38ae6fd
3. Stopped service (process kill)
4. Restarted service with same DATABASE_URL
5. GET /api/v1/invoices/2a21d7e3-29c6-4435-a401-9cd6676d936a - returned same invoice

### Result: VERIFIED
Invoice persisted across service restarts using Supabase PostgreSQL database.

---

## Telemetry Database Schema

### Telemetry Tables

#### truck_positions
| Column | Type | Constraints |
|--------|------|-------------|
| time | TIMESTAMP WITH TZ | PRIMARY KEY (composite) |
| truck_id | UUID | PRIMARY KEY (composite) |
| driver_id | UUID | NULLABLE |
| trip_id | UUID | NULLABLE |
| latitude | FLOAT | NOT NULL |
| longitude | FLOAT | NOT NULL |
| altitude_m | FLOAT | NULLABLE |
| accuracy_m | FLOAT | NULLABLE |
| h3_index | TEXT | NOT NULL |
| speed_kmh | FLOAT | NOT NULL, DEFAULT 0 |
| heading | FLOAT | NULLABLE |
| signal_strength | INTEGER | NULLABLE |
| connection_type | TEXT | NULLABLE |
| ignition_on | BOOLEAN | NULLABLE |
| region_code | TEXT | NOT NULL |

#### truck_telemetry
| Column | Type | Constraints |
|--------|------|-------------|
| time | TIMESTAMP WITH TZ | PRIMARY KEY (composite) |
| truck_id | UUID | PRIMARY KEY (composite) |
| engine_rpm | INTEGER | NULLABLE |
| engine_temp_c | FLOAT | NULLABLE |
| fuel_level_pct | FLOAT | NULLABLE |
| fuel_rate_lph | FLOAT | NULLABLE |
| odometer_km | FLOAT | NULLABLE |
| battery_voltage | FLOAT | NULLABLE |
| dtc_codes | TEXT[] | NULLABLE |
| check_engine | BOOLEAN | NULLABLE |
| cargo_temp_c | FLOAT | NULLABLE |
| ambient_temp_c | FLOAT | NULLABLE |
| humidity_pct | FLOAT | NULLABLE |
| harsh_braking | BOOLEAN | NULLABLE |
| harsh_acceleration | BOOLEAN | NULLABLE |
| sharp_turn | BOOLEAN | NULLABLE |
| region_code | TEXT | NOT NULL |

---

## Telemetry Ports and Endpoints

### Telemetry Ingress
- **Port**: 8006
- **Base URL**: http://127.0.0.1:8006
- **API Prefix**: /api/v1

#### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/v1/telemetry | Persist telemetry position update |
| GET | /api/v1/telemetry/truck/{truck_id} | Get latest positions for a truck |
| POST | /api/v1/ingest/position | HTTP fallback position ingest (buffered) |
| POST | /api/v1/ingest/telemetry | HTTP fallback telemetry ingest (buffered) |

---

## Telemetry Persistence Verification

### Test Performed
1. Started Telemetry Ingress with DATABASE_URL pointing to Supabase pooler
2. POST /api/v1/telemetry for truck_id=1af055fa-58d9-4624-9ccf-e800580d1f11
3. Stopped service (process kill)
4. Restarted service with same DATABASE_URL
5. GET /api/v1/telemetry/truck/1af055fa-58d9-4624-9ccf-e800580d1f11 - returned latest position

### Result: VERIFIED
Telemetry position persisted across service restarts using Supabase PostgreSQL database.

---

## Internal Communication (gRPC)

### gRPC Ports

| Service | gRPC Port | Protocol |
|---------|-----------|----------|
| Fleet Service | 50051 | gRPC (insecure) |
| Identity Service | 50052 | gRPC (insecure) |
| Matching Engine | 50053 | gRPC (insecure) |
| FinTrack Service | 50054 | gRPC (insecure) |
| Telemetry Ingress | 50056 | gRPC (insecure) |

### gRPC Contract (Fleet Service)

**Service**: `FleetService`  
**Method**: `GetTruckDetails(GetTruckRequest) returns (TruckResponse)`

#### Request
```protobuf
message GetTruckRequest {
  string truck_id = 1;
}
```

#### Response
```protobuf
message TruckResponse {
  string id = 1;
  string owner_id = 2;
  string license_plate = 3;
  string truck_type = 4;
  int32 load_capacity_kg = 5;
  string status = 6;
  string region_code = 7;
  optional string vin = 8;
  optional string make = 9;
  optional string model = 10;
  bool has_refrigeration = 11;
}
```

### gRPC Verification (Task 4.1)

**Test Performed**:
1. Started Fleet Service HTTP (port 8002) + gRPC server (port 50051)
2. Started Matching Engine (port 8003)
3. POST /api/v1/trucks/location to Matching Engine with truck_id=1af055fa-58d9-4624-9ccf-e800580d1f11
4. Matching Engine called Fleet Service via gRPC (port 50051) to fetch truck details
5. Logs confirmed: `[gRPC Client] Received response: truck_type=flatbed, load_capacity_kg=10000`

**Result**: VERIFIED - Matching Engine successfully fetched truck data via gRPC without using Fleet's HTTP port (8002)

### gRPC Contract (Identity Service)

**Service**: `IdentityService`  
**Method**: `GetUserDetails(GetUserRequest) returns (UserResponse)`

#### Request
```protobuf
message GetUserRequest {
  string user_id = 1;
}
```

#### Response
```protobuf
message UserResponse {
  string id = 1;
  string email = 2;
  string phone = 3;
  string full_name = 4;
  string role = 5;
  string kyc_status = 6;
  double reputation_score = 7;
  string region_code = 8;
  bool is_active = 10;
}
```

### gRPC Verification (Task 4.2)

**Test Performed**:
1. Started Identity Service HTTP (port 8001) + gRPC server (port 50052)
2. Started Fleet Service gRPC (port 50051)
3. Started Matching Engine (port 8003)
4. Step A: POST /api/v1/shipments with non-existent user_id -> **403 Forbidden** (User not found)
5. Step B: POST /api/v1/shipments with valid user (role=shipper) -> **201 Created**
6. Logs confirmed: `[gRPC Client] Received response: role=shipper, is_active=True`

**Result**: VERIFIED - Matching Engine successfully verified shipper via gRPC to Identity Service on port 50052

### gRPC Contract (FinTrack Service)

**Service**: `FinTrackService`  
**Method**: `CreateInvoice(InvoiceRequest) returns (InvoiceResponse)`

#### Request
```protobuf
message InvoiceRequest {
  string shipment_id = 1;
  string shipper_id = 2;
  double amount = 3;
  string currency = 4;
}
```

#### Response
```protobuf
message InvoiceResponse {
  string invoice_id = 1;
  string shipment_id = 2;
  double amount = 3;
  string currency = 4;
  string status = 5;
}
```

### gRPC Verification (Task 4.3)

**Test Performed**:
1. Started FinTrack Service HTTP (port 8004) + gRPC server (port 50054)
2. Started Identity Service gRPC (port 50052)
3. Started Fleet Service gRPC (port 50051)
4. Started Matching Engine (port 8003)
5. POST /api/v1/shipments with valid shipper
6. Matching Engine calculated price (719.22 EGP) and called FinTrack via gRPC
7. Checked DB: Invoice created with amount 719.22 EGP, status=pending

**Result**: VERIFIED - Matching Engine successfully created invoice via gRPC to FinTrack Service on port 50054

## Event Bus (NATS JetStream)

### Overview
Asynchronous event-driven communication using NATS JetStream for decoupling services and triggering the AI Brain.

### NATS Configuration
- **URL**: `nats://localhost:4222` (configurable via `NATS_URL` env var)
- **Stream**: `SHIPMENT`, `IDENTITY`, `FLEET`, `MATCHING`, `FINTRACK`, `AGENT`, `TELEMETRY`
- **Retention**: 7 days

### Event Subjects

| Subject | Publisher | Subscriber | Description |
|---------|-----------|------------|-------------|
| `shipment.created` | Matching Engine | Agent Orchestrator | New shipment registered |
| `shipment.assigned` | Matching Engine | Fleet Service | Shipment matched to truck |
| `telemetry.geofence.entered` | Telemetry Ingress | Agent Orchestrator | Truck entered geofence |

### Event Payload (shipment.created)
```json
{
  "event_id": "uuid",
  "event_type": "shipment.created",
  "timestamp": "2026-04-15T12:00:00Z",
  "source_service": "matching-engine",
  "payload": {
    "shipment_id": "uuid",
    "pickup_h3": "893e628e67bffff",
    "dropoff_h3": "893f5ba66b3ffff",
    "cargo_type": "general"
  }
}
```

### Implementation
- **Library**: `nats-py` (async)
- **Publisher**: `naql_common.events.EventBus.publish(DomainEvent)`
- **Subscriber**: Durable consumer with `deliver_policy=NEW`

### Task 5.1 Status
- [VERIFIED] Matching Engine publishes `shipment.created` after gRPC calls
- [VERIFIED] Agent Orchestrator subscribes to `shipment.created` via NATS
- [VERIFIED] End-to-end: Agent received "AI Brain: Received new shipment task..." log
- [VERIFIED] JetStream persistence: Agent received missed message after restart

### NATS Setup (Windows)
- **Method**: Windows binary (nats-server v2.10.7)
- **Location**: `C:\nats-temp\nats-server-v2.10.7-windows-amd64\nats-server.exe -js`
- **Port**: 4222 (client), 8222 (monitoring)
- **JetStream**: Enabled with 7-day retention

## Real-time Telemetry (MQTT)

### MQTT Broker Configuration
- **Port**: 1883 (TCP)
- **Protocol**: MQTT v3.1.1 / v5.0
- **Authentication**: Anonymous (allowed)

### Topic Structure
| Topic | Description | Payload |
|-------|-------------|---------|
| `naql/telemetry/v1/{truck_id}/pos` | Truck position updates | `{"lat": float, "lon": float, "speed": float, "fuel": float}` |
| `naql/telemetry/v1/{truck_id}/telemetry` | Vehicle telemetry | Engine, fuel, temperature data |

### Implementation
- **Library**: `paho-mqtt` (async client with background loop)
- **Subscriber**: Telemetry-Ingress service (port 8006)
- **Persistence**: Saves to `truck_positions` table in Supabase

### Task 6.1 Status
- [VERIFIED] NATS MQTT Gateway enabled on port 1883
- [VERIFIED] Telemetry-Ingress connected to MQTT broker
- [VERIFIED] Simulation script publishes to naql/telemetry/v1/{truck_id}/pos
- [VERIFIED] DB records created: truck_positions table shows positions every 2 seconds

### MQTT Broker Setup
- **Method**: NATS Server v2.10.18 with MQTT Gateway
- **Config**: nats_mqtt.conf (mqtt { port: 1883 }, listen: 127.0.0.1:4222)
- **NATS Port**: 4222, **MQTT Port**: 1883

### Simulation Script
- **Location**: `scripts/simulate_truck_mqtt.py`
- **Truck ID**: 1af055fa-58d9-4624-9ccf-e800580d1f11
- **Publishes**: Position every 2 seconds to `naql/telemetry/v1/{truck_id}/pos`

## Agent Orchestration Logic (LangGraph)

### Graph Structure
- **Location**: `services/agent-orchestrator/app/logic/graph.py`
- **Nodes**: Planner -> Fleet-Analyzer -> Decision-Maker

### Node Functions
| Node | Function | Data Source |
|------|----------|-------------|
| Planner | Analyze shipment requirements | NATS event payload |
| Fleet-Analyzer | Fetch available trucks | Fleet Service (HTTP + gRPC) |
| Decision-Maker | Rank trucks by score | Logic-based matching |

### Decision Scoring Algorithm
- Capacity match: +50 (>=5000kg), +30 (>=2000kg)
- Fuel level: +30% weight
- Availability bonus: +20

### Task 7.1 Status
- [VERIFIED] LangGraph state machine with 3 nodes (Planner -> Fleet-Analyzer -> Decision-Maker)
- [VERIFIED] gRPC integration for truck details
- [VERIFIED] Trigger on NATS shipment.created event
- [VERIFIED] NATS connection on Windows - Agent receives shipment.created events
- [VERIFIED] End-to-end flow: Shipment created -> NATS event published -> Agent subscribes and processes -> Decision output

## GraphQL Gateway

### Overview
Strawberry GraphQL-based unified API gateway that orchestrates all backend services.

### Configuration
- **Port**: 4001 (4000 was in use)
- **Base URL**: http://127.0.0.1:4001
- **Endpoint**: /graphql

### Service Communication
The Gateway acts as a pure orchestrator - it does NOT access the DB directly. All data is fetched via HTTP calls to backend services:
- Identity Service (8001) - User authentication and profiles
- Fleet Service (8002) - Truck data
- Matching Engine (8003) - Shipments
- FinTrack Service (8004) - Pricing and balances
- Agent Orchestrator (8005) - AI chat

### GraphQL Schema

#### Types
```graphql
type User {
  id: ID!
  email: String!
  phone: String!
  fullName: String!
  role: String!
  kycStatus: String!
  reputationScore: Float!
  regionCode: String!
  isActive: Boolean!
  createdAt: DateTime!
}

type Truck {
  id: ID!
  ownerId: ID!
  licensePlate: String!
  truckType: String!
  loadCapacityKg: Int!
  status: String!
  regionCode: String!
  hasRefrigeration: Boolean!
}

type Shipment {
  id: ID!
  referenceNumber: String!
  clientId: ID!
  regionCode: String!
  status: String!
  originAddress: String!
  originLat: Float!
  originLng: Float!
  originH3Index: String!
  destAddress: String!
  destLat: Float!
  destLng: Float!
  destH3Index: String!
  commodityType: String!
  weightKg: Float!
  distanceKm: Float
  quotedPriceEgp: Float
  createdAt: DateTime!
}
```

#### Queries
```graphql
type Query {
  me: User
  user(userId: ID!): User
  truck(truckId: ID!): Truck
  trucks(page: Int, pageSize: Int, truckType: String, regionCode: String): [Truck!]!
  shipment(shipmentId: ID!): Shipment
  shipments(clientId: ID, status: String): [Shipment!]!
  balance(userId: ID!): Balance
}
```

#### Mutations
```graphql
type Mutation {
  register(input: RegisterInput!): AuthPayload!
  login(input: LoginInput!): AuthPayload!
  requestMatch(input: MatchRequestInput!): MatchResult!
  getQuote(input: QuoteInput!): PriceQuote!
  chat(input: ChatInput!): ChatResponse!
}
```

### Task 8.1 Status
- [VERIFIED] Strawberry GraphQL schema with all types and resolvers
- [VERIFIED] ServiceClient uses sync httpx for HTTP calls to backend services
- [VERIFIED] Gateway running on port 4001
- [VERIFIED] GraphQL playground accessible at http://localhost:4001/graphql
- [VERIFIED] Shipment query returns full shipment data
- [VERIFIED] Truck query returns truck data
- [VERIFIED] Gateway is pure orchestrator - no direct DB access

### GitHub Repository
- **URL**: https://github.com/ibrahimhady131-cloud/Naql-ai-Core
- **Branch**: main
- **Python Version**: 3.11 (C:\Users\sd\AppData\Local\Programs\Python\Python311\python.exe)

### Task 9.1 Status
- [VERIFIED] Apollo Client configured to point to http://localhost:4001/graphql
- [VERIFIED] Dashboard uses live GraphQL queries (trucks, shipments, getLiveLocation)
- [VERIFIED] Live Map polls every 3 seconds for truck position (ID: 1af055fa-58d9-4624-9ccf-e800580d1f11)
- [VERIFIED] npm install completed in frontend/

### UI/UX Schema: Truck Status Color Mapping (Dashboard Legend)
- **available**: Emerald (`bg-emerald-500`)
- **en_route**: Blue (`bg-blue-500`)
- **loading**: Amber (`bg-amber-500`)
- **offline**: Gray (`bg-gray-500`)

### UI/UX Layout Architecture: Sidebar-over-Map (Dashboard)
- **Map**: Primary canvas (Leaflet) inside the dashboard layout.
- **Sidebar overlay**: `LifecycleSidebar` renders as a fixed overlay on the right side.
- **Z-index hierarchy**:
  - Map layer: default Leaflet panes (base)
  - Sidebar overlay: must be higher than all map panes (target z-index: `1001`)
- **Interaction rule**: Clicking a truck marker opens the sidebar without unmounting the map.

### Simulation Schema: Mega Flood Truck Status Randomization
- **File**: `scripts/mega_simulator.py`
- **Purpose**: Create varied, realistic operational states for 100 trucks.
- **Status set**:
  - `available`
  - `en_route`
  - `loading`
  - `offline` (optional, used to simulate dropouts)
- **Rule**: Each registered truck is assigned a randomized status at creation time and/or periodically updated.

### Architecture: Gateway-Centric (ALL Frontend Traffic via Port 4001)
- **Principle**: Frontend (5000) NEVER calls backend services directly. All traffic MUST go through GraphQL Gateway on port 4001.
- **Payment Flow**:
  - Frontend calls GraphQL Mutation `getPaymentLink` on Gateway (4001)
  - Gateway calls FinTrack Service (8004) via HTTP internally
  - Gateway returns payment portal URL to Frontend
- **CORS**: All services (identity, fleet, matching, fintrack, telemetry, agent, gateway) must allow http://localhost:5000

### Phase 12: Production Readiness - 100% COMPLETE
- **AI Reasoning Feed**: Step-by-Step Timeline with icons (Planner, Fleet, Decision, Match)
- **Trip Playback**: Replay button animates truck marker from tripHistory coordinates
- **Payment Mutation**: `getPaymentLink(invoiceId, amountEgp, userId) -> PaymentLinkResult`
- **Payment Flow**: Gateway (4001) -> FinTrack (8004) -> Local Portal (http://localhost:8004/api/v1/payments/portal/{link_id})
- **UI Polish**: Map 800px height, Sidebar z-index 1001, Status colors (Emerald/Blue/Amber/Gray)
- **Verification**: Payment link returns local portal URL (not Paymob external)
