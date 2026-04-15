import StatCard from "@/components/ui/stat-card";

const DEMO_SHIPMENTS = [
  { id: "SHP-0041", origin: "Sokhna Port", dest: "6th October City", commodity: "Steel", weight: 30000, price: 1820, status: "in_transit", driver: "Ahmed Hassan" },
  { id: "SHP-0042", origin: "Alexandria Port", dest: "Cairo Ring Road", commodity: "Grain", weight: 22000, price: 2150, status: "pending", driver: null },
  { id: "SHP-0043", origin: "Damietta Port", dest: "10th Ramadan City", commodity: "Chemicals", weight: 18000, price: 1950, status: "delivered", driver: "Omar Khaled" },
  { id: "SHP-0044", origin: "Port Said", dest: "Cairo", commodity: "Containers", weight: 25000, price: 2800, status: "in_transit", driver: "Youssef Ibrahim" },
  { id: "SHP-0045", origin: "Cairo", dest: "Alexandria", commodity: "Cement", weight: 15000, price: 1200, status: "pending", driver: null },
  { id: "SHP-0046", origin: "Suez", dest: "Cairo", commodity: "Electronics", weight: 5000, price: 980, status: "delivered", driver: "Karim Nasser" },
];

const STATUS_BADGE: Record<string, string> = {
  pending: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
  in_transit: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
  delivered: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400",
};

export default function ShipmentsPage() {
  const totalRevenue = DEMO_SHIPMENTS.reduce((sum, s) => sum + s.price, 0);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Shipments</h1>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Track and manage active shipments
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Total Shipments" value={DEMO_SHIPMENTS.length} color="blue" />
        <StatCard label="In Transit" value={DEMO_SHIPMENTS.filter((s) => s.status === "in_transit").length} color="blue" />
        <StatCard label="Pending Match" value={DEMO_SHIPMENTS.filter((s) => s.status === "pending").length} color="yellow" />
        <StatCard label="Total Revenue" value={`${totalRevenue.toLocaleString()} EGP`} color="green" />
      </div>

      <div className="rounded-xl border border-[var(--border)] bg-[var(--card-bg)] overflow-hidden">
        <table className="min-w-full text-sm">
          <thead className="bg-gray-100 dark:bg-gray-800">
            <tr>
              <th className="px-4 py-3 text-left font-medium text-gray-600 dark:text-gray-300">ID</th>
              <th className="px-4 py-3 text-left font-medium text-gray-600 dark:text-gray-300">Origin</th>
              <th className="px-4 py-3 text-left font-medium text-gray-600 dark:text-gray-300">Destination</th>
              <th className="px-4 py-3 text-left font-medium text-gray-600 dark:text-gray-300">Commodity</th>
              <th className="px-4 py-3 text-left font-medium text-gray-600 dark:text-gray-300">Weight (kg)</th>
              <th className="px-4 py-3 text-left font-medium text-gray-600 dark:text-gray-300">Price (EGP)</th>
              <th className="px-4 py-3 text-left font-medium text-gray-600 dark:text-gray-300">Driver</th>
              <th className="px-4 py-3 text-left font-medium text-gray-600 dark:text-gray-300">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--border)]">
            {DEMO_SHIPMENTS.map((shipment) => (
              <tr key={shipment.id} className="hover:bg-gray-50 dark:hover:bg-gray-900">
                <td className="px-4 py-3 font-mono text-xs">{shipment.id}</td>
                <td className="px-4 py-3">{shipment.origin}</td>
                <td className="px-4 py-3">{shipment.dest}</td>
                <td className="px-4 py-3">{shipment.commodity}</td>
                <td className="px-4 py-3">{shipment.weight.toLocaleString()}</td>
                <td className="px-4 py-3">{shipment.price.toLocaleString()}</td>
                <td className="px-4 py-3">{shipment.driver ?? <span className="text-gray-400 italic">Unassigned</span>}</td>
                <td className="px-4 py-3">
                  <span className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_BADGE[shipment.status]}`}>
                    {shipment.status.replace("_", " ")}
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
