import { useMemo } from "react";
import StatsBar from "../components/StatsBar";
import ThreatMap from "../components/ThreatMap";
import { useDashboardStore } from "../store/dashboardStore";

function describeAction(level) {
  if (level === "high") return "Escalate to containment and isolate account activity.";
  if (level === "medium") return "Flag for analyst verification and monitor retries.";
  return "Monitor passively and append to entity baseline.";
}

export default function ResponseOpsPage() {
  const alerts = useDashboardStore((state) => state.alerts.items);

  const queue = useMemo(
    () =>
      [...alerts]
        .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
        .slice(0, 6)
        .map((alert) => ({
          ...alert,
          action: describeAction(alert.severity),
        })),
    [alerts]
  );

  return (
    <div className="space-y-4">
      <section className="soc-glass p-5 md:p-6">
        <p className="soc-kicker">Incident Response</p>
        <h1 className="soc-title mt-2">Prioritized operational queue for active mitigation decisions.</h1>
        <p className="mt-2 max-w-2xl text-sm text-soc-muted">
          This view keeps response actions readable for morning handoff: what triggered, how severe it is, and what the next action should be.
        </p>
      </section>

      <StatsBar />

      <section className="grid grid-cols-1 gap-4 xl:grid-cols-[1.5fr_1fr]">
        <ThreatMap />

        <section className="soc-glass h-[390px] overflow-y-auto p-4">
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-[0.16em] text-soc-muted">Response Queue</h2>
          <div className="space-y-2">
            {queue.length === 0 ? (
              <div className="rounded-xl border border-dashed border-soc-border bg-soc-panelSoft/35 p-4 text-sm text-soc-muted">
                No incidents queued right now.
              </div>
            ) : null}

            {queue.map((item) => (
              <article key={item.id} className="rounded-xl border border-soc-border/70 bg-soc-panelSoft/45 p-3">
                <div className="mb-1 flex items-center justify-between gap-2 text-xs text-soc-muted">
                  <span className="uppercase tracking-[0.16em]">{item.severity}</span>
                  <span>{new Date(item.timestamp).toLocaleTimeString()}</span>
                </div>
                <p className="text-sm text-soc-text">{item.message}</p>
                <p className="mt-2 text-xs text-soc-muted">Action: {item.action}</p>
              </article>
            ))}
          </div>
        </section>
      </section>
    </div>
  );
}
