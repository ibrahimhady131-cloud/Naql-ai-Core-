-- Naql.ai CockroachDB Schema
-- Transactional data: Users, Trucks, Shipments, Trips, Payments
-- Designed for regional sharding (partitioned by region_code)

-- ============================================================
-- USERS & IDENTITY
-- ============================================================

CREATE TABLE IF NOT EXISTS users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           STRING(255) NOT NULL UNIQUE,
    phone           STRING(20) NOT NULL UNIQUE,
    password_hash   STRING(255) NOT NULL,
    full_name       STRING(255) NOT NULL,
    national_id     STRING(14),           -- Egyptian National ID (14 digits)
    role            STRING(30) NOT NULL DEFAULT 'client_individual',
    kyc_status      STRING(20) NOT NULL DEFAULT 'pending',
    reputation_score DECIMAL(3,2) DEFAULT 5.00,
    region_code     STRING(10) NOT NULL,  -- Cell: EG-CAI, EG-ALX, etc.
    profile_image_url STRING(500),
    is_active       BOOLEAN NOT NULL DEFAULT true,
    last_login_at   TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at      TIMESTAMPTZ,

    INDEX idx_users_region (region_code),
    INDEX idx_users_role (role),
    INDEX idx_users_kyc (kyc_status),
    INDEX idx_users_phone (phone)
);

CREATE TABLE IF NOT EXISTS user_documents (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id),
    document_type   STRING(50) NOT NULL,   -- national_id, driving_license, commercial_register
    document_number STRING(100),
    document_url    STRING(500) NOT NULL,
    verified        BOOLEAN NOT NULL DEFAULT false,
    verified_at     TIMESTAMPTZ,
    expires_at      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

    INDEX idx_user_docs_user (user_id)
);

CREATE TABLE IF NOT EXISTS api_keys (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id),
    key_hash        STRING(255) NOT NULL UNIQUE,
    name            STRING(100) NOT NULL,
    scopes          STRING[] NOT NULL DEFAULT ARRAY[],
    rate_limit_tier STRING(20) NOT NULL DEFAULT 'standard', -- standard, premium, enterprise
    is_active       BOOLEAN NOT NULL DEFAULT true,
    last_used_at    TIMESTAMPTZ,
    expires_at      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

    INDEX idx_api_keys_user (user_id)
);

-- ============================================================
-- FLEET MANAGEMENT
-- ============================================================

CREATE TABLE IF NOT EXISTS trucks (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id        UUID NOT NULL REFERENCES users(id),
    vin             STRING(17) UNIQUE,
    license_plate   STRING(20) NOT NULL UNIQUE,
    truck_type      STRING(20) NOT NULL,    -- quarter, half, full, jumbo, trailer, etc.
    make            STRING(50),
    model           STRING(50),
    year            INT2,
    load_capacity_kg INT NOT NULL,
    has_refrigeration BOOLEAN NOT NULL DEFAULT false,
    has_gps_tracker BOOLEAN NOT NULL DEFAULT true,
    telemetry_device_id STRING(100),
    insurance_expiry TIMESTAMPTZ,
    license_expiry  TIMESTAMPTZ,
    status          STRING(20) NOT NULL DEFAULT 'offline',
    region_code     STRING(10) NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at      TIMESTAMPTZ,

    INDEX idx_trucks_owner (owner_id),
    INDEX idx_trucks_type (truck_type),
    INDEX idx_trucks_status (status),
    INDEX idx_trucks_region (region_code)
);

CREATE TABLE IF NOT EXISTS truck_maintenance (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    truck_id        UUID NOT NULL REFERENCES trucks(id),
    maintenance_type STRING(50) NOT NULL,  -- scheduled, emergency, inspection
    description     STRING(1000),
    cost_egp        DECIMAL(12,2),
    odometer_km     INT,
    performed_at    TIMESTAMPTZ NOT NULL,
    next_due_at     TIMESTAMPTZ,
    performed_by    STRING(255),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

    INDEX idx_maintenance_truck (truck_id),
    INDEX idx_maintenance_next_due (next_due_at)
);

-- ============================================================
-- SHIPMENTS & ORDERS
-- ============================================================

CREATE TABLE IF NOT EXISTS shipments (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    reference_number STRING(20) NOT NULL UNIQUE,  -- Human-readable: NQL-20250101-XXXX
    client_id       UUID NOT NULL REFERENCES users(id),
    
    -- Origin
    origin_address  STRING(500) NOT NULL,
    origin_lat      DECIMAL(10,7) NOT NULL,
    origin_lng      DECIMAL(10,7) NOT NULL,
    origin_h3_index STRING(15) NOT NULL,       -- H3 hex index (resolution 9)
    origin_hub      STRING(50),                -- Nearest logistics hub
    
    -- Destination
    dest_address    STRING(500) NOT NULL,
    dest_lat        DECIMAL(10,7) NOT NULL,
    dest_lng        DECIMAL(10,7) NOT NULL,
    dest_h3_index   STRING(15) NOT NULL,
    dest_hub        STRING(50),
    
    -- Cargo details
    commodity_type  STRING(100) NOT NULL,
    description     STRING(1000),
    weight_kg       DECIMAL(10,2) NOT NULL,
    volume_cbm      DECIMAL(8,2),              -- Cubic meters
    requires_refrigeration BOOLEAN NOT NULL DEFAULT false,
    temperature_min_c DECIMAL(4,1),
    temperature_max_c DECIMAL(4,1),
    is_hazardous    BOOLEAN NOT NULL DEFAULT false,
    hazmat_class    STRING(10),
    
    -- Requirements
    required_truck_type STRING(20),
    containers_count INT DEFAULT 1,
    pickup_window_start TIMESTAMPTZ NOT NULL,
    pickup_window_end TIMESTAMPTZ NOT NULL,
    delivery_deadline TIMESTAMPTZ,
    
    -- Pricing
    quoted_price_egp DECIMAL(12,2),
    fuel_cost_egp   DECIMAL(10,2),
    toll_cost_egp   DECIMAL(10,2),
    service_fee_egp DECIMAL(10,2),
    insurance_fee_egp DECIMAL(10,2),
    
    -- State
    status          STRING(30) NOT NULL DEFAULT 'draft',
    status_history  JSONB NOT NULL DEFAULT '[]',
    
    -- Metadata
    distance_km     DECIMAL(8,2),
    estimated_duration_min INT,
    region_code     STRING(10) NOT NULL,
    notes           STRING(2000),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    INDEX idx_shipments_client (client_id),
    INDEX idx_shipments_status (status),
    INDEX idx_shipments_origin_h3 (origin_h3_index),
    INDEX idx_shipments_dest_h3 (dest_h3_index),
    INDEX idx_shipments_region (region_code),
    INDEX idx_shipments_pickup (pickup_window_start),
    INDEX idx_shipments_ref (reference_number)
);

-- Versioned audit trail for shipment state changes
CREATE TABLE IF NOT EXISTS shipment_audit_log (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    shipment_id     UUID NOT NULL REFERENCES shipments(id),
    version         INT NOT NULL,
    previous_status STRING(30),
    new_status      STRING(30) NOT NULL,
    changed_by      UUID REFERENCES users(id),
    change_reason   STRING(500),
    metadata        JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

    INDEX idx_audit_shipment (shipment_id),
    UNIQUE (shipment_id, version)
);

-- ============================================================
-- TRIPS (Active transport)
-- ============================================================

CREATE TABLE IF NOT EXISTS trips (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    shipment_id     UUID NOT NULL REFERENCES shipments(id),
    driver_id       UUID NOT NULL REFERENCES users(id),
    truck_id        UUID NOT NULL REFERENCES trucks(id),
    
    -- Route
    planned_route_polyline TEXT,             -- Encoded polyline
    actual_route_polyline TEXT,
    planned_distance_km DECIMAL(8,2),
    actual_distance_km DECIMAL(8,2),
    
    -- Timing
    accepted_at     TIMESTAMPTZ,
    pickup_arrived_at TIMESTAMPTZ,
    picked_up_at    TIMESTAMPTZ,
    delivered_at    TIMESTAMPTZ,
    estimated_arrival TIMESTAMPTZ,
    
    -- Real-time
    current_lat     DECIMAL(10,7),
    current_lng     DECIMAL(10,7),
    current_speed_kmh DECIMAL(5,1),
    current_heading DECIMAL(5,2),
    
    -- Fuel & tolls
    fuel_consumed_liters DECIMAL(8,2),
    toll_checkpoints JSONB DEFAULT '[]',     -- [{name, cost_egp, passed_at}]
    
    -- Rating
    client_rating   DECIMAL(2,1),            -- 1.0 to 5.0
    driver_rating   DECIMAL(2,1),
    
    status          STRING(20) NOT NULL DEFAULT 'assigned',
    region_code     STRING(10) NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

    INDEX idx_trips_shipment (shipment_id),
    INDEX idx_trips_driver (driver_id),
    INDEX idx_trips_truck (truck_id),
    INDEX idx_trips_status (status),
    INDEX idx_trips_region (region_code)
);

-- ============================================================
-- FINANCIAL (Ledger, Payments, Escrow)
-- ============================================================

CREATE TABLE IF NOT EXISTS ledger_accounts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id),
    account_type    STRING(30) NOT NULL,     -- driver_earnings, client_credit, platform_revenue, escrow
    balance_egp     DECIMAL(14,2) NOT NULL DEFAULT 0.00,
    currency        STRING(3) NOT NULL DEFAULT 'EGP',
    is_frozen       BOOLEAN NOT NULL DEFAULT false,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (user_id, account_type)
);

CREATE TABLE IF NOT EXISTS transactions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    reference_number STRING(30) NOT NULL UNIQUE,
    from_account_id UUID REFERENCES ledger_accounts(id),
    to_account_id   UUID REFERENCES ledger_accounts(id),
    amount_egp      DECIMAL(14,2) NOT NULL,
    transaction_type STRING(30) NOT NULL,    -- payment, escrow_hold, escrow_release, refund, payout
    payment_method  STRING(30),              -- fawry, paymob, valu, bank_transfer, etc.
    shipment_id     UUID REFERENCES shipments(id),
    
    status          STRING(20) NOT NULL DEFAULT 'pending',
    gateway_ref     STRING(255),             -- External payment gateway reference
    metadata        JSONB,
    
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at    TIMESTAMPTZ,

    INDEX idx_tx_from (from_account_id),
    INDEX idx_tx_to (to_account_id),
    INDEX idx_tx_shipment (shipment_id),
    INDEX idx_tx_status (status),
    INDEX idx_tx_type (transaction_type)
);

CREATE TABLE IF NOT EXISTS escrow_holds (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    shipment_id     UUID NOT NULL REFERENCES shipments(id),
    payer_account_id UUID NOT NULL REFERENCES ledger_accounts(id),
    amount_egp      DECIMAL(14,2) NOT NULL,
    status          STRING(20) NOT NULL DEFAULT 'held',  -- held, released, refunded
    held_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    released_at     TIMESTAMPTZ,
    release_to      UUID REFERENCES ledger_accounts(id),

    INDEX idx_escrow_shipment (shipment_id)
);

-- ============================================================
-- MATCHING ENGINE SUPPORT
-- ============================================================

CREATE TABLE IF NOT EXISTS driver_preferences (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    driver_id       UUID NOT NULL REFERENCES users(id) UNIQUE,
    preferred_routes JSONB DEFAULT '[]',      -- [{origin_region, dest_region}]
    max_distance_km INT DEFAULT 500,
    min_price_egp   DECIMAL(10,2),
    preferred_cargo STRING[] DEFAULT ARRAY[],
    blacklisted_clients UUID[] DEFAULT ARRAY[],
    auto_accept     BOOLEAN NOT NULL DEFAULT false,
    working_hours   JSONB,                    -- {start: "06:00", end: "22:00", days: [0..6]}
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS match_history (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    shipment_id     UUID NOT NULL REFERENCES shipments(id),
    driver_id       UUID NOT NULL REFERENCES users(id),
    score           DECIMAL(5,3) NOT NULL,    -- Matching score 0.000 - 1.000
    factors         JSONB NOT NULL,           -- {distance: 0.8, rating: 0.9, price: 0.7, ...}
    offered_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    responded_at    TIMESTAMPTZ,
    response        STRING(20),               -- accepted, rejected, expired, cancelled

    INDEX idx_match_shipment (shipment_id),
    INDEX idx_match_driver (driver_id)
);

-- ============================================================
-- NOTIFICATIONS
-- ============================================================

CREATE TABLE IF NOT EXISTS notifications (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id),
    title           STRING(200) NOT NULL,
    body            STRING(1000) NOT NULL,
    notification_type STRING(50) NOT NULL,
    reference_type  STRING(50),              -- shipment, trip, payment, etc.
    reference_id    UUID,
    is_read         BOOLEAN NOT NULL DEFAULT false,
    channel         STRING(20) NOT NULL DEFAULT 'push', -- push, sms, email, in_app
    sent_at         TIMESTAMPTZ,
    read_at         TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

    INDEX idx_notif_user (user_id),
    INDEX idx_notif_unread (user_id, is_read) WHERE is_read = false
);
