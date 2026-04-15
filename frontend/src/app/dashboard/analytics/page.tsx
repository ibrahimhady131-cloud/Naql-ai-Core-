import StatCard from "@/components/ui/stat-card";

const ROUTE_STATS = [
  { route: "Sokhna \u2192 6th October", trips: 128, avgPrice: 1820, avgTime: "3h 15m" },
  { route: "Cairo \u2192 Alexandria", trips: 95, avgPrice: 2150, avgTime: "2h 45m" },
  { route: "Port Said \u2192 Cairo", trips: 73, avgPrice: 2800, avgTime: "3h 30m" },
  { route: "Damietta \u2192 10th Ramadan", trips: 61, avgPrice: 1950, avgTime: "4h 00m" },
  { route: "Suez \u2192 Cairo", trips: 54, avgPrice: 980, avgTime: "1h 45m" },
  { route: "Cairo \u2192 Aswan", trips: 32, avgPrice: 4500, avgTime: "10h 00m" },
];

export default function AnalyticsPage() {
  const totalTrips = ROUTE_STATS.reduce((sum, r) => sum + r.trips, 0);
  const totalRevenue = ROUTE_STATS.reduce((sum, r) => sum + r.trips * r.avgPrice, 0);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Analytics</h1>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Route performance and operational metrics
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Total Trips (30d)" value={totalTrips} trend="up" color="blue" />
        <StatCard label="Revenue (30d)" value={`${(totalRevenue / 1000).toFixed(0)}K EGP`} trend="up" color="green" />
        <StatCard label="Avg Match Time" value="4.2 min" subtitle="Driver assignment" color="blue" />
        <StatCard label="On-Time Delivery" value="94.3%" trend="up" color="green" />
      </div>

      {/* Route performance table */}
      <div className="rounded-xl border border-[var(--border)] bg-[var(--card-bg)] overflow-hidden">
        <div className="px-4 py-3 border-b border-[var(--border)]">
          <h2 className="text-lg font-semibold">Top Routes (Last 30 Days)</h2>
        </div>
        <table className="min-w-full text-sm">
          <thead className="bg-gray-100 dark:bg-gray-800">
            <tr>
              <th className="px-4 py-3 text-left font-medium text-gray-600 dark:text-gray-300">Route</th>
              <th className="px-4 py-3 text-right font-medium text-gray-600 dark:text-gray-300">Trips</th>
              <th className="px-4 py-3 text-right font-medium text-gray-600 dark:text-gray-300">Avg Price (EGP)</th>
              <th className="px-4 py-3 text-right font-medium text-gray-600 dark:text-gray-300">Avg Duration</th>
              <th className="px-4 py-3 text-right font-medium text-gray-600 dark:text-gray-300">Revenue (EGP)</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--border)]">
            {ROUTE_STATS.map((route) => (
              <tr key={route.route} className="hover:bg-gray-50 dark:hover:bg-gray-900">
                <td className="px-4 py-3 font-medium">{route.route}</td>
                <td className="px-4 py-3 text-right">{route.trips}</td>
                <td className="px-4 py-3 text-right">{route.avgPrice.toLocaleString()}</td>
                <td className="px-4 py-3 text-right">{route.avgTime}</td>
                <td className="px-4 py-3 text-right font-medium">{(route.trips * route.avgPrice).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
