import { useMemo } from "react";
import { useDashboardStore } from "../store/dashboardStore";

function StatCard({ label, value, accent }) {
  return (
    <article className="soc-glass group relative overflow-hidden rounded-[22px] px-4 py-4 transition-all duration-300 hover:border-soc-electric/45">
      <div className="pointer-events-none absolute inset-x-10 top-0 h-px bg-gradient-to-r from-transparent via-white/60 to-transparent opacity-40" />
      <p className="text-[10px] font-semibold uppercase tracking-[0.24em] text-soc-muted">{label}</p>
      <p className={`mt-3 text-3xl font-semibold leading-none ${accent}`}>{value}</p>
    </article>
  );
}

export default function StatsBar() {
  const stats = useDashboardStore((state) => state.stats.data);

  const cards = useMemo(
    () => [
      {
        label: "Total Transactions",
        value: stats.totalTransactions.toLocaleString(),
        accent: "text-soc-electric",
      },
      {
        label: "Hacker Detections",
        value: stats.hackerDetections.toLocaleString(),
        accent: "text-soc-red",
      },
      {
        label: "Avg Risk Score",
        value: Number(stats.avgRiskScore).toFixed(2),
        accent: "text-soc-amber",
      },
      {
        label: "Live Alerts",
        value: stats.liveAlerts.toLocaleString(),
        accent: "text-soc-green",
      },
    ],
    [stats]
  );

  return (
    <section className="grid grid-cols-2 gap-3 xl:grid-cols-4">
      {cards.map((card) => (
        <StatCard key={card.label} {...card} />
      ))}
    </section>
  );
}
