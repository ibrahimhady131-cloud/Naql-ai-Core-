-- Naql.ai TimescaleDB Schema
-- Time-series data: GPS tracking, sensor telemetry, analytics
-- Leverages TimescaleDB hypertables for efficient time-based queries

-- ============================================================
-- GPS TRACKING (Core telemetry)
-- ============================================================

CREATE TABLE IF NOT EXISTS truck_positions (
    time            TIMESTAMPTZ NOT NULL,
    truck_id        UUID NOT NULL,
    driver_id       UUID,
    trip_id         UUID,
    
    -- Position
    latitude        DOUBLE PRECISION NOT NULL,
    longitude       DOUBLE PRECISION NOT NULL,
    altitude_m      REAL,
    accuracy_m      REAL,
    h3_index        TEXT NOT NULL,            -- H3 hex (resolution 9)
    
    -- Motion
    speed_kmh       REAL NOT NULL DEFAULT 0,
    heading         REAL,                      -- 0-360 degrees
    
    -- Network
    signal_strength INT2,                      -- dBm
    connection_type TEXT,                       -- 4g, 3g, 2g, satellite
    
    -- Status flags
    ignition_on     BOOLEAN DEFAULT true,
    region_code     TEXT NOT NULL
);

-- Convert to hypertable (7-day chunks)
SELECT create_hypertable('truck_positions', 'time',
    chunk_time_interval => INTERVAL '7 days',
    if_not_exists => TRUE
);

-- Compression policy: compress chunks older than 2 days
ALTER TABLE truck_positions SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'truck_id',
    timescaledb.compress_orderby = 'time DESC'
);

SELECT add_compression_policy('truck_positions', INTERVAL '2 days', if_not_exists => TRUE);

-- Retention: drop chunks older than 90 days (raw data)
SELECT add_retention_policy('truck_positions', INTERVAL '90 days', if_not_exists => TRUE);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_positions_truck_time 
    ON truck_positions (truck_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_positions_trip 
    ON truck_positions (trip_id, time DESC) WHERE trip_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_positions_h3 
    ON truck_positions (h3_index, time DESC);
CREATE INDEX IF NOT EXISTS idx_positions_region 
    ON truck_positions (region_code, time DESC);

-- ============================================================
-- SENSOR TELEMETRY (OBD-II / IoT sensors)
-- ============================================================

CREATE TABLE IF NOT EXISTS truck_telemetry (
    time            TIMESTAMPTZ NOT NULL,
    truck_id        UUID NOT NULL,
    
    -- Engine
    engine_rpm      INT,
    engine_temp_c   REAL,
    fuel_level_pct  REAL,                     -- 0-100%
    fuel_rate_lph   REAL,                     -- Liters per hour
    odometer_km     REAL,
    
    -- Diagnostics
    battery_voltage REAL,
    dtc_codes       TEXT[],                    -- Diagnostic Trouble Codes
    check_engine    BOOLEAN DEFAULT false,
    
    -- Environment (for refrigerated trucks)
    cargo_temp_c    REAL,
    ambient_temp_c  REAL,
    humidity_pct    REAL,
    
    -- Driving behavior
    harsh_braking   BOOLEAN DEFAULT false,
    harsh_acceleration BOOLEAN DEFAULT false,
    sharp_turn      BOOLEAN DEFAULT false,
    
    region_code     TEXT NOT NULL
);

SELECT create_hypertable('truck_telemetry', 'time',
    chunk_time_interval => INTERVAL '7 days',
    if_not_exists => TRUE
);

ALTER TABLE truck_telemetry SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'truck_id',
    timescaledb.compress_orderby = 'time DESC'
);

SELECT add_compression_policy('truck_telemetry', INTERVAL '2 days', if_not_exists => TRUE);
SELECT add_retention_policy('truck_telemetry', INTERVAL '90 days', if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS idx_telemetry_truck_time 
    ON truck_telemetry (truck_id, time DESC);

-- ============================================================
-- GEOFENCE EVENTS
-- ============================================================

CREATE TABLE IF NOT EXISTS geofence_events (
    time            TIMESTAMPTZ NOT NULL,
    truck_id        UUID NOT NULL,
    trip_id         UUID,
    
    event_type      TEXT NOT NULL,             -- entered, exited
    geofence_name   TEXT NOT NULL,             -- sokhna_port, cairo_ring_road, etc.
    geofence_type   TEXT NOT NULL,             -- hub, restricted_zone, toll_gate, client_site
    
    latitude        DOUBLE PRECISION NOT NULL,
    longitude       DOUBLE PRECISION NOT NULL,
    
    dwell_time_sec  INT,                       -- Time spent in zone (on exit)
    region_code     TEXT NOT NULL
);

SELECT create_hypertable('geofence_events', 'time',
    chunk_time_interval => INTERVAL '30 days',
    if_not_exists => TRUE
);

CREATE INDEX IF NOT EXISTS idx_geofence_truck 
    ON geofence_events (truck_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_geofence_name 
    ON geofence_events (geofence_name, time DESC);

-- ============================================================
-- SPEED & ROUTE VIOLATIONS
-- ============================================================

CREATE TABLE IF NOT EXISTS driving_violations (
    time            TIMESTAMPTZ NOT NULL,
    truck_id        UUID NOT NULL,
    driver_id       UUID NOT NULL,
    trip_id         UUID,
    
    violation_type  TEXT NOT NULL,             -- speeding, route_deviation, rest_violation, geofence_breach
    severity        TEXT NOT NULL,             -- info, warning, critical
    
    -- Context
    speed_kmh       REAL,
    speed_limit_kmh REAL,
    deviation_km    REAL,                      -- Distance from planned route
    
    latitude        DOUBLE PRECISION NOT NULL,
    longitude       DOUBLE PRECISION NOT NULL,
    
    acknowledged    BOOLEAN DEFAULT false,
    region_code     TEXT NOT NULL
);

SELECT create_hypertable('driving_violations', 'time',
    chunk_time_interval => INTERVAL '30 days',
    if_not_exists => TRUE
);

CREATE INDEX IF NOT EXISTS idx_violations_driver 
    ON driving_violations (driver_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_violations_trip 
    ON driving_violations (trip_id, time DESC);

-- ============================================================
-- CONTINUOUS AGGREGATES (Materialized views for dashboards)
-- ============================================================

-- Hourly position summary per truck
CREATE MATERIALIZED VIEW IF NOT EXISTS truck_position_hourly
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 hour', time) AS bucket,
    truck_id,
    region_code,
    AVG(speed_kmh) AS avg_speed,
    MAX(speed_kmh) AS max_speed,
    COUNT(*) AS sample_count,
    FIRST(latitude, time) AS start_lat,
    FIRST(longitude, time) AS start_lng,
    LAST(latitude, time) AS end_lat,
    LAST(longitude, time) AS end_lng
FROM truck_positions
GROUP BY bucket, truck_id, region_code
WITH NO DATA;

SELECT add_continuous_aggregate_policy('truck_position_hourly',
    start_offset => INTERVAL '3 hours',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour',
    if_not_exists => TRUE
);

-- Daily fleet analytics
CREATE MATERIALIZED VIEW IF NOT EXISTS fleet_daily_stats
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 day', time) AS bucket,
    region_code,
    COUNT(DISTINCT truck_id) AS active_trucks,
    AVG(speed_kmh) AS avg_speed,
    COUNT(*) AS total_pings
FROM truck_positions
WHERE speed_kmh > 0
GROUP BY bucket, region_code
WITH NO DATA;

SELECT add_continuous_aggregate_policy('fleet_daily_stats',
    start_offset => INTERVAL '2 days',
    end_offset => INTERVAL '1 day',
    schedule_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);
