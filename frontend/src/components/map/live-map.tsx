"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import mapboxgl from "mapbox-gl";
import "mapbox-gl/dist/mapbox-gl.css";
import { LOGISTICS_HUBS, MAP_CENTER, MAP_ZOOM, MAPBOX_TOKEN } from "@/lib/config";

/** Represents a truck position update from the telemetry service. */
export interface TruckPosition {
  truck_id: string;
  latitude: number;
  longitude: number;
  speed_kmh: number;
  heading: number;
  status: "available" | "en_route" | "loading" | "offline";
}

/** Color mapping for truck statuses. */
const STATUS_COLORS: Record<TruckPosition["status"], string> = {
  available: "#10b981",
  en_route: "#3b82f6",
  loading: "#f59e0b",
  offline: "#6b7280",
};

interface LiveMapProps {
  /** Truck positions to render on the map. */
  positions?: TruckPosition[];
  /** Whether to show logistics hub geofence circles. */
  showHubs?: boolean;
  /** Optional CSS class for the map container. */
  className?: string;
}

export default function LiveMap({
  positions = [],
  showHubs = true,
  className = "",
}: LiveMapProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<mapboxgl.Map | null>(null);
  const markersRef = useRef<Map<string, mapboxgl.Marker>>(new Map());
  const [mapReady, setMapReady] = useState(false);

  /* ── Initialise Mapbox map ────────────────────────────── */
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    if (!MAPBOX_TOKEN) {
      // Render a placeholder when no token is configured
      setMapReady(false);
      return;
    }

    mapboxgl.accessToken = MAPBOX_TOKEN;

    const map = new mapboxgl.Map({
      container: containerRef.current,
      style: "mapbox://styles/mapbox/dark-v11",
      center: MAP_CENTER,
      zoom: MAP_ZOOM,
    });

    map.addControl(new mapboxgl.NavigationControl(), "top-right");

    map.on("load", () => {
      setMapReady(true);

      /* Draw logistics hub geofence circles */
      if (showHubs) {
        Object.entries(LOGISTICS_HUBS).forEach(([id, hub]) => {
          map.addSource(`hub-${id}`, {
            type: "geojson",
            data: createCircleGeoJSON(hub.lng, hub.lat, hub.radius_km),
          });

          map.addLayer({
            id: `hub-fill-${id}`,
            type: "fill",
            source: `hub-${id}`,
            paint: {
              "fill-color": "#3b82f6",
              "fill-opacity": 0.1,
            },
          });

          map.addLayer({
            id: `hub-border-${id}`,
            type: "line",
            source: `hub-${id}`,
            paint: {
              "line-color": "#3b82f6",
              "line-width": 1.5,
              "line-dasharray": [2, 2],
            },
          });

          /* Hub label */
          map.addSource(`hub-label-${id}`, {
            type: "geojson",
            data: {
              type: "Feature",
              geometry: { type: "Point", coordinates: [hub.lng, hub.lat] },
              properties: { name: hub.name },
            },
          });

          map.addLayer({
            id: `hub-text-${id}`,
            type: "symbol",
            source: `hub-label-${id}`,
            layout: {
              "text-field": ["get", "name"],
              "text-size": 11,
              "text-anchor": "center",
            },
            paint: {
              "text-color": "#93c5fd",
              "text-halo-color": "#0f172a",
              "text-halo-width": 1,
            },
          });
        });
      }
    });

    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /* ── Update truck markers when positions change ─────── */
  const updateMarkers = useCallback(() => {
    if (!mapRef.current || !mapReady) return;

    const activeIds = new Set(positions.map((p) => p.truck_id));

    // Remove markers for trucks no longer in the data
    markersRef.current.forEach((marker, id) => {
      if (!activeIds.has(id)) {
        marker.remove();
        markersRef.current.delete(id);
      }
    });

    // Add or update markers
    positions.forEach((pos) => {
      const existing = markersRef.current.get(pos.truck_id);

      if (existing) {
        existing.setLngLat([pos.longitude, pos.latitude]);
        const el = existing.getElement();
        el.style.backgroundColor = STATUS_COLORS[pos.status];
      } else {
        const el = document.createElement("div");
        el.style.width = "14px";
        el.style.height = "14px";
        el.style.borderRadius = "50%";
        el.style.backgroundColor = STATUS_COLORS[pos.status];
        el.style.border = "2px solid white";
        el.style.boxShadow = "0 0 6px rgba(0,0,0,0.4)";
        el.title = `${pos.truck_id} — ${pos.speed_kmh.toFixed(0)} km/h`;

        const marker = new mapboxgl.Marker({ element: el })
          .setLngLat([pos.longitude, pos.latitude])
          .setPopup(
            new mapboxgl.Popup({ offset: 12 }).setHTML(
              `<div style="font-family:sans-serif;font-size:13px">
                <strong>${pos.truck_id}</strong><br/>
                Speed: ${pos.speed_kmh.toFixed(0)} km/h<br/>
                Status: <span style="color:${STATUS_COLORS[pos.status]}">${pos.status}</span>
              </div>`
            )
          )
          .addTo(mapRef.current!);

        markersRef.current.set(pos.truck_id, marker);
      }
    });
  }, [positions, mapReady]);

  useEffect(() => {
    updateMarkers();
  }, [updateMarkers]);

  /* ── Render ──────────────────────────────────────────── */
  if (!MAPBOX_TOKEN) {
    return (
      <div
        className={`flex items-center justify-center rounded-xl bg-gray-900 text-gray-400 ${className}`}
      >
        <div className="text-center">
          <p className="text-lg font-medium">Map Unavailable</p>
          <p className="mt-1 text-sm">
            Set <code className="rounded bg-gray-800 px-1.5 py-0.5 text-blue-400">NEXT_PUBLIC_MAPBOX_TOKEN</code> to enable the live map.
          </p>
        </div>
      </div>
    );
  }

  return <div ref={containerRef} className={`rounded-xl ${className}`} />;
}

/* ── Helpers ───────────────────────────────────────────── */

/** Create a GeoJSON polygon approximating a circle. */
function createCircleGeoJSON(
  lng: number,
  lat: number,
  radiusKm: number,
  steps = 64
): GeoJSON.Feature<GeoJSON.Polygon> {
  const coords: [number, number][] = [];
  for (let i = 0; i <= steps; i++) {
    const angle = (i / steps) * 2 * Math.PI;
    const dLat = (radiusKm / 111.32) * Math.cos(angle);
    const dLng =
      (radiusKm / (111.32 * Math.cos((lat * Math.PI) / 180))) *
      Math.sin(angle);
    coords.push([lng + dLng, lat + dLat]);
  }
  return {
    type: "Feature",
    geometry: { type: "Polygon", coordinates: [coords] },
    properties: {},
  };
}
