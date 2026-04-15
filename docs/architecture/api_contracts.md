# Naql.ai API Contracts

## Overview

Naql.ai exposes two API layers:
1. **GraphQL Gateway** (port 4000) — For external clients (Mobile, Web, ERP)
2. **gRPC Internal** (ports 50051-50055) — For service-to-service communication

All APIs use JWT Bearer authentication.

## GraphQL API

### Endpoint
```
POST /graphql
```

### Authentication
```
Authorization: Bearer <access_token>
```

### Queries

#### Get Current User
```graphql
query Me {
  me {
    id
    email
    fullName
    role
    kycStatus
    reputationScore
    regionCode
  }
}
```

#### Search Trucks
```graphql
query Trucks($type: String, $region: String) {
  trucks(truckType: $type, regionCode: $region) {
    id
    licensePlate
    truckType
    loadCapacityKg
    status
    hasRefrigeration
  }
}
```

#### Get Balance
```graphql
query Balance($userId: String!) {
  balance(userId: $userId) {
    availableEgp
    heldEgp
    totalEgp
  }
}
```

### Mutations

#### Register
```graphql
mutation Register($input: RegisterInput!) {
  register(input: $input) {
    userId
    accessToken
    refreshToken
    role
    regionCode
  }
}
```

#### Request Match
```graphql
mutation RequestMatch($input: MatchRequestInput!) {
  requestMatch(input: $input) {
    matchId
    candidates {
      driverId
      truckId
      score
      distanceKm
      etaMinutes
      driverRating
    }
    totalSearched
  }
}
```

#### Get Quote
```graphql
mutation GetQuote($input: QuoteInput!) {
  getQuote(input: $input) {
    quoteId
    totalEgp
    fuelCostEgp
    tollCostEgp
    serviceFeeEgp
    insuranceFeeEgp
    validUntil
  }
}
```

#### Chat with AI Agent
```graphql
mutation Chat($input: ChatInput!) {
  chat(input: $input) {
    sessionId
    response
    intent
  }
}
```

## REST API Endpoints

Each microservice exposes REST endpoints for direct access:

### Identity Service (`:8001`)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/auth/register` | Register new user |
| POST | `/api/v1/auth/login` | Login |
| GET | `/api/v1/users/me` | Get current user |
| GET | `/api/v1/users/{id}` | Get user by ID |
| PATCH | `/api/v1/users/{id}` | Update user |
| POST | `/api/v1/users/{id}/kyc` | Verify KYC |
| GET | `/api/v1/users` | List users |

### Fleet Service (`:8002`)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/trucks` | Register truck |
| GET | `/api/v1/trucks/{id}` | Get truck |
| PATCH | `/api/v1/trucks/{id}/status` | Update status |
| GET | `/api/v1/trucks` | List trucks |
| GET | `/api/v1/trucks/owner/{id}` | Get by owner |
| POST | `/api/v1/trucks/{id}/maintenance` | Add maintenance |

### Matching Engine (`:8003`)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/match` | Request match |
| POST | `/api/v1/match/available-trucks` | Find nearby trucks |
| POST | `/api/v1/match/decision` | Driver decision |
| POST | `/api/v1/trucks/location` | Update position |

### FinTrack Service (`:8004`)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/quotes` | Create quote |
| POST | `/api/v1/escrow` | Create escrow |
| POST | `/api/v1/escrow/release` | Release escrow |
| POST | `/api/v1/payments` | Process payment |
| GET | `/api/v1/balance/{userId}` | Get balance |
| GET | `/api/v1/transactions/{userId}` | Transaction history |

### Agent Orchestrator (`:8005`)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/chat` | Chat with agent |
| GET | `/api/v1/chat/history/{sessionId}` | Get chat history |
| POST | `/api/v1/agent/event` | Process event |
| POST | `/api/v1/agent/preferences` | Store preference |
| GET | `/api/v1/agent/preferences/{userId}` | Get preferences |

### Telemetry Ingress (`:8006`)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/ingest/position` | Ingest position |
| POST | `/api/v1/ingest/telemetry` | Ingest telemetry |
| GET | `/api/v1/telemetry/stats` | Processing stats |

## gRPC Services

See `proto/naql/v1/services.proto` for the full Protocol Buffer definitions.

## MQTT Topics

| Topic Pattern | Description | QoS |
|--------------|-------------|-----|
| `naql/truck/{id}/position` | GPS position updates | 0 |
| `naql/truck/{id}/telemetry` | OBD-II sensor data | 0 |
| `naql/truck/{id}/alert` | Driver alerts | 1 |

## NATS JetStream Subjects

| Stream | Subjects | Retention |
|--------|----------|-----------|
| IDENTITY | `identity.>` | 7 days |
| FLEET | `fleet.>` | 7 days |
| MATCHING | `matching.>` | 7 days |
| SHIPMENT | `shipment.>` | 7 days |
| FINTRACK | `fintrack.>` | 7 days |
| AGENT | `agent.>` | 7 days |
| TELEMETRY | `telemetry.>` | 7 days |
