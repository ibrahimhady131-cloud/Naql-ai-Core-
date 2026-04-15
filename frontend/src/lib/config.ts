/** Shared configuration constants for the Naql.ai frontend. */

/** GraphQL Gateway URL (server-side calls use internal Docker network). */
export const GRAPHQL_URL =
  process.env.NEXT_PUBLIC_GRAPHQL_URL ?? "http://localhost:4001/graphql";

/** WebSocket URL for real-time telemetry subscriptions. */
export const WS_URL =
  process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:4001/graphql";

/** Telemetry REST polling fallback (used when WS is unavailable). */
export const TELEMETRY_URL =
  process.env.NEXT_PUBLIC_TELEMETRY_URL ?? "http://localhost:8006";

/** Mapbox public token — must be set via env var for map to render. */
export const MAPBOX_TOKEN = process.env.NEXT_PUBLIC_MAPBOX_TOKEN ?? "";

/** Default map center: Cairo, Egypt. */
export const MAP_CENTER: [number, number] = [31.2357, 30.0444]; // [lng, lat]

/** Default map zoom level. */
export const MAP_ZOOM = 6.5;

/** Egyptian logistics hub coordinates for geofence overlays. */
export const LOGISTICS_HUBS: Record<
  string,
  { name: string; lng: number; lat: number; radius_km: number }
> = {
  sokhna_port: {
    name: "Sokhna Port",
    lng: 32.3414,
    lat: 29.5952,
    radius_km: 5,
  },
  damietta_port: {
    name: "Damietta Port",
    lng: 31.8125,
    lat: 31.4175,
    radius_km: 4,
  },
  port_said: {
    name: "Port Said",
    lng: 32.3019,
    lat: 31.2653,
    radius_km: 5,
  },
  cairo_ring_road: {
    name: "Cairo Ring Road Hub",
    lng: 31.2357,
    lat: 30.0444,
    radius_km: 15,
  },
  "6th_october": {
    name: "6th of October City",
    lng: 30.9271,
    lat: 29.9569,
    radius_km: 8,
  },
  "10th_ramadan": {
    name: "10th of Ramadan City",
    lng: 31.7629,
    lat: 30.2975,
    radius_km: 6,
  },
  alexandria_port: {
    name: "Alexandria Port",
    lng: 29.8623,
    lat: 31.2001,
    radius_km: 5,
  },
  suez_canal_zone: {
    name: "Suez Canal Zone",
    lng: 32.5498,
    lat: 30.0048,
    radius_km: 10,
  },
};
