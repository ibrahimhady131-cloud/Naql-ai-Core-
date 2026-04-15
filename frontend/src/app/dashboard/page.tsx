"use client";

import { useQuery } from "@apollo/client";
import { gql } from "@apollo/client";
import { useEffect, useState } from "react";
import LiveMap, { type TruckPosition } from "@/components/map/live-map";
import StatCard from "@/components/ui/stat-card";

const TRUCK_ID = "1af055fa-58d9-4624-9ccf-e800580d1f11";

const TRUCKS_QUERY = gql`
  query GetTrucks {
    trucks(pageSize: 100) {
      id
      status
      licensePlate
      truckType
    }
  }
`;

const SHIPMENTS_QUERY = gql`
  query GetShipments {
    shipments {
      id
      referenceNumber
      status
      originAddress
      destAddress
      commodityType
      weightKg
    }
  }
`;

const LIVE_LOCATION_QUERY = gql`
  query GetLiveLocation($truckId: String!) {
    getLiveLocation(truckId: $truckId) {
      truckId
      timestamp
      latitude
      longitude
      speedKmh
    }
  }
`;

export default function DashboardPage() {
  const { data: trucksData, loading: trucksLoading } = useQuery(TRUCKS_QUERY);
  const { data: shipmentsData, loading: shipmentsLoading } = useQuery(SHIPMENTS_QUERY);
  const { data: locationData, loading: locationLoading, refetch: refetchLocation } = useQuery(LIVE_LOCATION_QUERY, {
    variables: { truckId: TRUCK_ID },
    pollInterval: 3000,
  });

  const [positions, setPositions] = useState<TruckPosition[]>([]);

  useEffect(() => {
    if (locationData?.getLiveLocation) {
      const loc = locationData.getLiveLocation;
      const newPos: TruckPosition = {
        truck_id: loc.truckId || TRUCK_ID,
        latitude: loc.latitude,
        longitude: loc.longitude,
        speed_kmh: loc.speedKmh || 0,
        heading: 0,
        status: "en_route",
      };
      setPositions([newPos]);
    }
  }, [locationData]);

  const trucks = trucksData?.trucks || [];
  const shipments = shipmentsData?.shipments || [];
  const activeTrucks = trucks.filter((t: { status: string }) => t.status === "available").length;
  const enRouteTrucks = trucks.filter((t: { status: string }) => t.status === "en_route").length;
  const pendingShipments = shipments.filter((s: { status: string }) => s.status === "pending").length;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">God View Dashboard</h1>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Real-time fleet monitoring across Egypt
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Active Trucks"
          value={trucksLoading ? "..." : activeTrucks}
          subtitle={`${trucks.length} total registered`}
          trend="up"
          color="green"
        />
        <StatCard
          label="En Route"
          value={trucksLoading ? "..." : enRouteTrucks}
          subtitle="Currently on delivery"
          trend="neutral"
          color="blue"
        />
        <StatCard
          label="Pending Shipments"
          value={shipmentsLoading ? "..." : pendingShipments}
          subtitle={`${shipments.length} total shipments`}
          trend="up"
          color="blue"
        />
        <StatCard
          label="Live Truck Speed"
          value={locationLoading ? "..." : `${locationData?.getLiveLocation?.speedKmh || 0} km/h`}
          subtitle={locationData?.getLiveLocation ? `Last update: ${new Date(locationData.getLiveLocation.timestamp).toLocaleTimeString()}` : "No data"}
          trend="neutral"
          color="green"
        />
      </div>

      <div className="rounded-xl border border-[var(--border)] bg-[var(--card-bg)] p-4">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-lg font-semibold">Live Fleet Map</h2>
          <div className="flex items-center gap-4 text-xs">
            <span className="flex items-center gap-1.5">
              <span className="inline-block h-2.5 w-2.5 rounded-full bg-emerald-500" />
              Available
            </span>
            <span className="flex items-center gap-1.5">
              <span className="inline-block h-2.5 w-2.5 rounded-full bg-blue-500" />
              En Route
            </span>
            <span className="flex items-center gap-1.5">
              <span className="inline-block h-2.5 w-2.5 rounded-full bg-amber-500" />
              Loading
            </span>
            <span className="flex items-center gap-1.5">
              <span className="inline-block h-2.5 w-2.5 rounded-full bg-gray-500" />
              Offline
            </span>
          </div>
        </div>
        <LiveMap
          positions={positions}
          showHubs
          className="h-[500px] w-full"
        />
      </div>
    </div>
  );
}
