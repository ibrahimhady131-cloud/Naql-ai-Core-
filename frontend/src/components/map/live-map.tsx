"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { MapContainer, TileLayer, Marker, Popup, Circle, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import "leaflet.markercluster";
import "leaflet.markercluster/dist/MarkerCluster.css";
import "leaflet.markercluster/dist/MarkerCluster.Default.css";
import { LOGISTICS_HUBS, MAP_CENTER, MAP_ZOOM } from "@/lib/config";

export interface TruckPosition {
  truck_id: string;
  latitude: number;
  longitude: number;
  speed_kmh: number;
  heading: number;
  status: "available" | "en_route" | "loading" | "offline";
}

const STATUS_COLORS: Record<TruckPosition["status"], string> = {
  available: "#10b981",
  en_route: "#3b82f6",
  loading: "#f59e0b",
  offline: "#6b7280",
};

function createTruckIcon(status: TruckPosition["status"]) {
  return L.divIcon({
    className: "",
    html: `<div style="width:14px;height:14px;background-color:${STATUS_COLORS[status]};border:2px solid white;border-radius:50%;box-shadow:0 0 6px rgba(0,0,0,0.4);"></div>`,
    iconSize: [14, 14],
    iconAnchor: [7, 7],
  });
}

interface LiveMapProps {
  positions?: TruckPosition[];
  showHubs?: boolean;
  className?: string;
  onTruckClick?: (truck: TruckPosition) => void;
}

function MapUpdater({ positions }: { positions: TruckPosition[] }) {
  const map = useMap();
  useEffect(() => {
    if (positions.length > 0) {
      const latest = positions[0];
      map.setView([latest.latitude, latest.longitude], map.getZoom());
    }
  }, [positions, map]);
  return null;
}

export default function LiveMap({
  positions = [],
  showHubs = true,
  className = "",
  onTruckClick,
}: LiveMapProps) {
  const [isClient, setIsClient] = useState(false);
  const clusterGroupRef = useRef<L.MarkerClusterGroup | null>(null);

  useEffect(() => {
    setIsClient(true);
  }, []);

  useEffect(() => {
    if (isClient && clusterGroupRef.current && positions.length > 0) {
      const cluster = clusterGroupRef.current;
      cluster.clearLayers();
      
      positions.forEach((pos) => {
        const marker = L.marker([pos.latitude, pos.longitude], {
          icon: createTruckIcon(pos.status),
        });
        
        marker.bindPopup(`
          <div style="font-family:sans-serif;font-size:13px">
            <strong>${pos.truck_id}</strong><br/>
            Speed: ${pos.speed_kmh.toFixed(0)} km/h<br/>
            Status: <span style="color:${STATUS_COLORS[pos.status]}">${pos.status}</span>
          </div>
        `);
        
        if (onTruckClick) {
          marker.on("click", () => onTruckClick(pos));
        }
        
        cluster.addLayer(marker);
      });
    }
  }, [positions, isClient, onTruckClick]);

  if (!isClient) {
    return (
      <div className={`flex items-center justify-center rounded-xl bg-gray-900 text-gray-400 ${className}`} style={{ height: 400 }}>
        <p className="text-lg font-medium">Loading map...</p>
      </div>
    );
  }

  const handleMapReady = useCallback((map: L.Map) => {
    clusterGroupRef.current = L.markerClusterGroup({
      chunkedLoading: true,
      spiderfyOnMaxZoom: true,
      showCoverageOnHover: false,
      maxClusterRadius: 50,
    });
    map.addLayer(clusterGroupRef.current);
  }, []);

  return (
    <div className={`rounded-xl overflow-hidden ${className}`} style={{ height: 400 }}>
      <MapContainer center={MAP_CENTER} zoom={MAP_ZOOM} style={{ height: "100%", width: "100%" }}>
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <MapUpdater positions={positions} />
        {showHubs && Object.entries(LOGISTICS_HUBS).map(([id, hub]) => (
          <Circle key={id} center={[hub.lat, hub.lng]} radius={hub.radius_km * 1000} pathOptions={{ color: "#3b82f6", fillColor: "#3b82f6", fillOpacity: 0.1 }} />
        ))}
      </MapContainer>
    </div>
  );
}
