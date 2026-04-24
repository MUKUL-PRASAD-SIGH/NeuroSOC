import { useMemo, useState } from "react";
import AlertFeed from "../components/AlertFeed";
import SeverityTrendChart from "../components/Charts/SeverityTrendChart";
import { useDashboardStore } from "../store/dashboardStore";

function severityScore(level) {
  if (level === "high") return 3;
  if (level === "medium") return 2;
  return 1;
}

export default function IntelFeedPage() {
  const alerts = useDashboardStore((state) => state.alerts.items);
  const [filter, setFilter] = useState("all");

  const filteredAlerts = useMemo(() => {
    const sorted = [...alerts].sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
    return filter === "all" ? sorted : sorted.filter((alert) => alert.severity === filter);
  }, [alerts, filter]);

  const hourlyTrend = useMemo(() => {
    const buckets = {};
    filteredAlerts.forEach((alert) => {
      const hour = new Date(alert.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
      if (!buckets[hour]) {
        buckets[hour] = 0;
      }
      buckets[hour] += severityScore(alert.severity);
    });

    return Object.entries(buckets)
      .map(([time, value]) => ({ time, high: value }))
      .slice(0, 12)
      .reverse();
  }, [filteredAlerts]);

  return (
    <div className="space-y-4">
      <section className="soc-glass p-5 md:p-6">
        <p className="soc-kicker">Threat Intel Stream</p>
        <h1 className="soc-title mt-2">Triage incoming alerts with severity-focused context.</h1>
        <div className="mt-4 flex flex-wrap gap-2">
          {["all", "high", "medium", "low"].map((level) => (
            <button
              type="button"
              key={level}
              onClick={() => setFilter(level)}
              className={`rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em] transition-colors ${
                filter === level
                  ? "border-soc-electric/45 bg-soc-electric/15 text-soc-electric"
                  : "border-soc-border bg-soc-panelSoft/45 text-soc-muted hover:border-soc-electric/35"
              }`}
            >
              {level}
            </button>
          ))}
        </div>
      </section>

      <section className="grid grid-cols-1 gap-4 xl:grid-cols-[1.3fr_1fr]">
        <SeverityTrendChart data={hourlyTrend.length ? hourlyTrend : [{ time: "--", high: 0 }]} />
        <AlertFeed showHeader={false} />
      </section>

      <section className="soc-glass p-4">
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-[0.16em] text-soc-muted">Latest Intelligence Entries</h2>
        <div className="overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead>
              <tr className="border-b border-soc-border/80 text-soc-muted">
                <th className="px-2 py-2 font-medium">Time</th>
                <th className="px-2 py-2 font-medium">Severity</th>
                <th className="px-2 py-2 font-medium">Message</th>
              </tr>
            </thead>
            <tbody>
              {filteredAlerts.slice(0, 10).map((alert) => (
                <tr key={alert.id} className="border-b border-soc-border/40 last:border-none">
                  <td className="px-2 py-2 text-soc-muted">{new Date(alert.timestamp).toLocaleString()}</td>
                  <td className="px-2 py-2 capitalize">{alert.severity}</td>
                  <td className="px-2 py-2 text-soc-text">{alert.message}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
