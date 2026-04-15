# Naql.ai System Architecture Document

## 1. Overview

Naql.ai is an autonomous logistics ecosystem designed specifically for the Egyptian market. It uses an **Event-Driven Microservices Architecture (EDMA)** with regional sharding ("Cells") to ensure nation-scale reliability, low-latency tracking, and AI-driven dispatching.

## 2. Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                     CLIENT LAYER                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐ │
│  │ Mobile   │  │ Web      │  │ ERP      │  │ Driver App       │ │
│  │ (B2B/B2C)│  │ Dashboard│  │ (SAP/    │  │ (Android/iOS)    │ │
│  │          │  │          │  │  Oracle) │  │                  │ │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └───────┬──────────┘ │
└───────┼──────────────┼──────────────┼───────────────┼────────────┘
        │              │              │               │
        ▼              ▼              ▼               ▼
┌──────────────────────────────────────────────────────────────────┐
│                   API GATEWAY LAYER                               │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │              GraphQL Gateway (Strawberry/FastAPI)           │  │
│  │                    Port 4000                                │  │
│  │   ┌─────────────┐  ┌──────────┐  ┌───────────────────┐   │  │
│  │   │ Auth        │  │ Rate     │  │ Request           │   │  │
│  │   │ Middleware  │  │ Limiter  │  │ Validation        │   │  │
│  │   └─────────────┘  └──────────┘  └───────────────────┘   │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
        │              │              │               │
        ▼              ▼              ▼               ▼
┌──────────────────────────────────────────────────────────────────┐
│                   SERVICE MESH (gRPC)                             │
│                                                                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐    │
│  │ Identity │  │ Fleet    │  │ Matching │  │ FinTrack     │    │
│  │ Service  │  │ Service  │  │ Engine   │  │ Service      │    │
│  │ :8001    │  │ :8002    │  │ :8003    │  │ :8004        │    │
│  └──────────┘  └──────────┘  └──────────┘  └──────────────┘    │
│                                                                   │
│  ┌──────────────────┐  ┌──────────────────────────────────┐     │
│  │ Agent            │  │ Telemetry Ingress                │     │
│  │ Orchestrator     │  │ (MQTT → Stream Processing)      │     │
│  │ :8005            │  │ :8006                            │     │
│  └──────────────────┘  └──────────────────────────────────┘     │
└──────────────────────────────────────────────────────────────────┘
        │              │              │               │
        ▼              ▼              ▼               ▼
┌──────────────────────────────────────────────────────────────────┐
│                   EVENT BUS & MESSAGING                           │
│  ┌────────────────────┐  ┌────────────────────────────────────┐ │
│  │ NATS JetStream     │  │ EMQX MQTT Broker                  │ │
│  │ (Domain Events)    │  │ (Truck Telemetry)                  │ │
│  │ :4222              │  │ :1883                              │ │
│  └────────────────────┘  └────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
        │              │              │               │
        ▼              ▼              ▼               ▼
┌──────────────────────────────────────────────────────────────────┐
│                   DATA LAYER                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ CockroachDB  │  │ TimescaleDB  │  │ Redis Stack          │  │
│  │ (Transact.)  │  │ (Time-Series)│  │ (Geospatial Cache)   │  │
│  │ :26257       │  │ :5432        │  │ :6379                │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

## 3. Regional Cell Architecture

Egypt is divided into operational "Cells" for data locality and failure isolation:

| Cell Code | Region | Major Cities |
|-----------|--------|-------------|
| EG-CAI | Greater Cairo | Cairo, Giza, Qalyubia |
| EG-ALX | Alexandria | Alexandria, Beheira, Matrouh |
| EG-SUE | Suez Canal Zone | Suez, Ismailia, Port Said, Red Sea |
| EG-DLT | Nile Delta | Sharqia, Dakahlia, Damietta, Gharbia |
| EG-UEG | Upper Egypt | Minya, Asyut, Sohag, Luxor, Aswan |
| EG-SIN | Sinai | North Sinai, South Sinai |
| EG-WST | Western Desert | New Valley |

## 4. AI Agent Architecture (LangGraph)

```
┌─────────────────────────────────────────────────────┐
│                 Agent Orchestrator                    │
│                                                       │
│  ┌───────────┐    ┌──────────────┐    ┌───────────┐ │
│  │  PLANNER  │───▶│  EXECUTOR    │───▶│ DISPATCHER│ │
│  │           │    │              │    │ (OR-Tools)│ │
│  │ Decompose │    │ Tool Calls   │    │           │ │
│  │ Intent    │    │ to Services  │    │ CVRP      │ │
│  └───────────┘    └──────────────┘    │ Solver    │ │
│       │                               └─────┬─────┘ │
│       │                                     │       │
│       ▼                                     ▼       │
│  ┌───────────────────────────────────────────────┐  │
│  │              SENTINEL (Monitor)                │  │
│  │                                                │  │
│  │  • Truck breakdowns → Re-assign                │  │
│  │  • Geofence violations → Alert                 │  │
│  │  • ETA deviations → Recalculate               │  │
│  │  • Speed violations → Warn driver             │  │
│  └───────────────────────────────────────────────┘  │
│                                                       │
│  ┌───────────────────────────────────────────────┐  │
│  │        VECTOR MEMORY (Pinecone)                │  │
│  │                                                │  │
│  │  • User preferences                           │  │
│  │  • Interaction history                         │  │
│  │  • Learned patterns (RAG)                      │  │
│  └───────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

## 5. Data Flow: Order to Delivery

```mermaid
sequenceDiagram
    participant C as Client (B2B/B2C)
    participant G as GraphQL Gateway
    participant A as AI Agent (Naql Brain)
    participant M as Matching Engine
    participant F as FinTrack Service
    participant D as Driver App
    participant T as Telemetry Ingress
    participant S as Sentinel

    C->>G: "Move 5 containers from Port Said to Cairo"
    G->>A: Forward request
    A->>A: Planner: Decompose intent
    A->>M: Query available Heavy Trailers (20km radius)
    M-->>A: Top 3 optimal drivers (rating/ETA)
    A->>F: Calculate quote (fuel + tolls + fees)
    F-->>A: Quote: 15,000 EGP (breakdown)
    A->>G: Return quote to client
    G->>C: "Quote: 15,000 EGP. Confirm?"

    C->>G: "Confirm and pay"
    G->>A: Process confirmation
    A->>F: Create escrow (15,000 EGP)
    A->>M: Assign best driver
    M->>D: Push job notification + optimized route
    D-->>A: Driver accepts

    A->>G: "Driver Mohamed en route. ETA 45 min"
    G->>C: Live tracking begins

    loop Real-time tracking
        D->>T: GPS position (MQTT every 5s)
        T->>S: Check geofences, speed, ETA
        S-->>A: Alert if anomaly detected
    end

    D->>A: Delivery confirmed
    A->>F: Release escrow to driver
    A->>C: "Delivered! Rate your experience"
```

## 6. Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Language | Python 3.12+ | All services |
| API Framework | FastAPI | REST + gRPC endpoints |
| GraphQL | Strawberry | External API gateway |
| Internal Comm | gRPC (protobuf) | Service-to-service |
| Event Bus | NATS JetStream | Async domain events |
| MQTT Broker | EMQX | Low-bandwidth telemetry |
| Transactional DB | CockroachDB | Orders, users, payments |
| Time-Series DB | TimescaleDB | GPS, sensors, telemetry |
| Cache/Geo Index | Redis Stack | Real-time geospatial |
| AI Framework | LangGraph | Agent orchestration |
| Optimization | Google OR-Tools | Route/dispatch solver |
| Vector DB | Pinecone | Agent long-term memory |
| Container | Docker | Service packaging |
| Orchestration | Kubernetes (EKS) | Production deployment |

## 7. Egyptian Context Adaptations

### Payment Integration
- **Fawry**: Cash payment network (kiosks, mobile)
- **Paymob**: Card payments + mobile wallets
- **Valu**: Buy-now-pay-later for enterprise
- **Bank transfers**: For large enterprise contracts

### Toll Calculation ("Cartas")
Automated toll calculation for major Egyptian routes:
- Cairo ↔ Alexandria (Desert Road): 180 EGP
- Cairo ↔ Suez: 120 EGP
- Cairo ↔ Delta: 80 EGP
- Cairo ↔ Upper Egypt: 200 EGP

### Truck Categories (Egyptian Market)
- ربع نقل (Quarter Load): 1,500 kg
- نص نقل (Half Load): 3,000 kg
- نقل كامل (Full Load): 7,000 kg
- جامبو (Jumbo): 15,000 kg
- مقطوره (Trailer): 25,000 kg
- مبرد (Refrigerated): 12,000 kg

### Geofence Zones
Pre-configured micro-geofences for major logistics hubs:
- Sokhna Port
- Damietta Port
- Alexandria Port
- 10th of Ramadan City
- 6th of October City
- Cairo Ring Road
- Suez Canal Zone
- Sadat City
