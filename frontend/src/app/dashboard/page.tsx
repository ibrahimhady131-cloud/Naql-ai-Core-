"use client";

import { useQuery, gql } from "@apollo/client";
import { useEffect, useState } from "react";
import LiveMap, { type TruckPosition } from "@/components/map/live-map";
import StatCard from "@/components/ui/stat-card";
import LifecycleSidebar from "@/components/ui/lifecycle-sidebar";

const TRUCKS_QUERY = gql`
  query GetTrucks {
    trucks(pageSize: 150) {
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

const SHIPMENT_BY_TRUCK_QUERY = gql`
  query GetShipmentByTruck($truckId: String!) {
    shipment_by_truck(truckId: $truckId) {
      id
      status
      referenceNumber
    }
  }
`;

export default function DashboardPage() {
  const { data: trucksData, loading: trucksLoading, error: trucksError, refetch: refetchTrucks } = useQuery(TRUCKS_QUERY, {
    pollInterval: 5000,
  });
  const { data: shipmentsData, loading: shipmentsLoading } = useQuery(SHIPMENTS_QUERY, {
    pollInterval: 5000,
  });

  const [positions, setPositions] = useState<TruckPosition[]>([]);
  const [selectedTruck, setSelectedTruck] = useState<TruckPosition | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [selectedShipmentId, setSelectedShipmentId] = useState<string | undefined>(undefined);

  // Query shipment by truck ID
  const { data: shipmentByTruckData } = useQuery(SHIPMENT_BY_TRUCK_QUERY, {
    variables: { truckId: selectedTruck?.truck_id },
    skip: !selectedTruck?.truck_id,
    pollInterval: 5000,
  });

  // Debug: Log GraphQL data
  console.log(">>> GraphQL trucksData:", trucksData);
  console.log(">>> GraphQL trucksError:", trucksError);
  console.log(">>> trucksLoading:", trucksLoading);
  console.log(">>> shipmentByTruckData:", shipmentByTruckData);

  useEffect(() => {
    if (trucksData?.trucks) {
      console.log(">>> Processing", trucksData.trucks.length, "trucks");
      const mockPositions: TruckPosition[] = trucksData.trucks.map((t: { id: string; status: string }) => ({
        truck_id: t.id,
        latitude: 30.0444 + (Math.random() - 0.5) * 2,
        longitude: 31.2357 + (Math.random() - 0.5) * 2,
        speed_kmh: Math.random() * 80,
        heading: Math.random() * 360,
        status: (t.status as string) || "available",
      }));
      setPositions(mockPositions);
    }
  }, [trucksData]);

  // Update shipment ID when truck is selected
  useEffect(() => {
    if (shipmentByTruckData?.shipment_by_truck?.id) {
      setSelectedShipmentId(shipmentByTruckData.shipment_by_truck.id);
    } else {
      setSelectedShipmentId(undefined);
    }
  }, [shipmentByTruckData]);

  const handleTruckClick = (truck: TruckPosition) => {
    setSelectedTruck(truck);
    setSelectedShipmentId(undefined); // Reset when clicking new truck
    setSidebarOpen(true);
  };

  const trucks = trucksData?.trucks || [];
  const shipments = shipmentsData?.shipments || [];
  const activeTrucks = trucks.filter((t: { status: string }) => t.status !== "offline").length;
  const enRouteTrucks = trucks.filter((t: { status: string }) => t.status === "en_route").length;
  const pendingShipments = shipments.filter((s: { status: string }) => s.status === "pending").length;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">God View Dashboard</h1>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Real-time fleet monitoring across Egypt - {trucks.length} trucks
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
          label="Fleet Status"
          value={trucksLoading ? "..." : "Live"}
          subtitle="MQTT connected"
          trend="neutral"
          color="green"
        />
      </div>

      <div className="rounded-xl border border-[var(--border)] bg-[var(--card-bg)] p-4">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-lg font-semibold">Live Fleet Map ({positions.length} trucks)</h2>
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
          className="h-[800px] w-full"
          onTruckClick={handleTruckClick}
        />
      </div>

      <LifecycleSidebar
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        shipmentId={selectedShipmentId}
        truckId={selectedTruck?.truck_id}
        truckStatus={selectedTruck?.status}
      />
    </div>
  );
}
