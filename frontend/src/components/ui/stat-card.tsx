interface StatCardProps {
  label: string;
  value: string | number;
  subtitle?: string;
  trend?: "up" | "down" | "neutral";
  color?: "blue" | "green" | "yellow" | "red" | "gray";
}

const COLOR_MAP = {
  blue: "bg-blue-600/10 text-blue-400",
  green: "bg-emerald-600/10 text-emerald-400",
  yellow: "bg-amber-600/10 text-amber-400",
  red: "bg-red-600/10 text-red-400",
  gray: "bg-gray-600/10 text-gray-400",
};

export default function StatCard({
  label,
  value,
  subtitle,
  trend,
  color = "blue",
}: StatCardProps) {
  return (
    <div className="rounded-xl border border-[var(--border)] bg-[var(--card-bg)] p-5">
      <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
        {label}
      </p>
      <div className="mt-2 flex items-baseline gap-2">
        <span className="text-2xl font-semibold tracking-tight">{value}</span>
        {trend && (
          <span className={`text-xs font-medium ${COLOR_MAP[color]}`}>
            {trend === "up" ? "\u2191" : trend === "down" ? "\u2193" : "\u2192"}
          </span>
        )}
      </div>
      {subtitle && (
        <p className="mt-1 text-xs text-gray-500 dark:text-gray-500">
          {subtitle}
        </p>
      )}
    </div>
  );
}
