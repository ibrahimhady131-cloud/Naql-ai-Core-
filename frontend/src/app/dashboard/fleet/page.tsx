import StatCard from "@/components/ui/stat-card";

const DEMO_TRUCKS = [
  { id: "TRK-001", plate: "ABC 1234", type: "Trailer", capacity: 25000, status: "available", region: "EG-CAI", driver: "Mohamed Ali" },
  { id: "TRK-002", plate: "XYZ 5678", type: "Jumbo", capacity: 15000, status: "en_route", region: "EG-SOK", driver: "Ahmed Hassan" },
  { id: "TRK-003", plate: "QRS 9012", type: "Refrigerated", capacity: 12000, status: "loading", region: "EG-ALX", driver: "Omar Khaled" },
  { id: "TRK-004", plate: "DEF 3456", type: "Full Load", capacity: 7000, status: "en_route", region: "EG-OCT", driver: "Youssef Ibrahim" },
  { id: "TRK-005", plate: "GHI 7890", type: "Tanker", capacity: 20000, status: "offline", region: "EG-RAM", driver: "Mahmoud Saeed" },
  { id: "TRK-006", plate: "JKL 2345", type: "Flatbed", capacity: 18000, status: "en_route", region: "EG-DKH", driver: "Karim Nasser" },
];

const STATUS_BADGE: Record<string, string> = {
  available: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400",
  en_route: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
  loading: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
  offline: "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400",
};

export default function FleetPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Fleet Management</h1>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Monitor and manage your truck fleet
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Total Trucks" value={DEMO_TRUCKS.length} color="blue" />
        <StatCard label="Available" value={DEMO_TRUCKS.filter((t) => t.status === "available").length} color="green" />
        <StatCard label="En Route" value={DEMO_TRUCKS.filter((t) => t.status === "en_route").length} color="blue" />
        <StatCard label="Offline" value={DEMO_TRUCKS.filter((t) => t.status === "offline").length} color="gray" />
      </div>

      <div className="rounded-xl border border-[var(--border)] bg-[var(--card-bg)] overflow-hidden">
        <table className="min-w-full text-sm">
          <thead className="bg-gray-100 dark:bg-gray-800">
            <tr>
              <th className="px-4 py-3 text-left font-medium text-gray-600 dark:text-gray-300">Truck ID</th>
              <th className="px-4 py-3 text-left font-medium text-gray-600 dark:text-gray-300">Plate</th>
              <th className="px-4 py-3 text-left font-medium text-gray-600 dark:text-gray-300">Type</th>
              <th className="px-4 py-3 text-left font-medium text-gray-600 dark:text-gray-300">Capacity (kg)</th>
              <th className="px-4 py-3 text-left font-medium text-gray-600 dark:text-gray-300">Driver</th>
              <th className="px-4 py-3 text-left font-medium text-gray-600 dark:text-gray-300">Region</th>
              <th className="px-4 py-3 text-left font-medium text-gray-600 dark:text-gray-300">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--border)]">
            {DEMO_TRUCKS.map((truck) => (
              <tr key={truck.id} className="hover:bg-gray-50 dark:hover:bg-gray-900">
                <td className="px-4 py-3 font-mono text-xs">{truck.id}</td>
                <td className="px-4 py-3">{truck.plate}</td>
                <td className="px-4 py-3">{truck.type}</td>
                <td className="px-4 py-3">{truck.capacity.toLocaleString()}</td>
                <td className="px-4 py-3">{truck.driver}</td>
                <td className="px-4 py-3 font-mono text-xs">{truck.region}</td>
                <td className="px-4 py-3">
                  <span className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_BADGE[truck.status]}`}>
                    {truck.status.replace("_", " ")}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
