import { useMemo } from "react";
import { useDashboardStore } from "../store/dashboardStore";

const verdictTone = {
  HACKER: "border-soc-red/50 bg-soc-red/12 text-soc-red",
  FORGETFUL_USER: "border-soc-amber/50 bg-soc-amber/12 text-soc-amber",
  LEGITIMATE: "border-soc-green/45 bg-soc-green/12 text-soc-green",
};

const ALERT_CAP = 50;

function formatAlertTime(timestamp) {
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) {
    return "--:--";
  }

  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function formatAlertScore(score) {
  const value = Number(score);
  if (!Number.isFinite(value)) {
    return 0;
  }

  return Math.round(value * 100);
}

export default function AlertFeed({ maxItems = null, showHeader = true }) {
  const alerts = useDashboardStore((state) => state.alerts.items);
  const loading = useDashboardStore((state) => state.alerts.loading);
  const status = useDashboardStore((state) => state.alerts.status);
  const openUserModal = useDashboardStore((state) => state.openUserModal);

  const sortedAlerts = useMemo(() => {
    const next = [...alerts].sort((a, b) => {
      const tA = new Date(a.timestamp).getTime() || 0;
      const tB = new Date(b.timestamp).getTime() || 0;
      return tB - tA;
    });

    const capped = next.slice(0, ALERT_CAP);
    return maxItems ? capped.slice(0, maxItems) : capped;
  }, [alerts, maxItems]);

  return (
    <section className="soc-glass flex h-full min-h-[360px] flex-col p-4 md:p-5">
      {showHeader ? (
        <div className="mb-4 flex items-center justify-between gap-3">
          <div>
            <p className="soc-kicker">Alert Feed</p>
            <h2 className="mt-2 text-xl font-semibold text-soc-text">Live analyst queue</h2>
          </div>
          <span className="rounded-full border border-soc-electric/30 bg-soc-electric/10 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-soc-electric">
            {loading ? "Hydrating" : status || "Idle"}
          </span>
        </div>
      ) : null}

      <div className="flex-1 max-h-[500px] space-y-3 overflow-y-auto pr-1">
        {!loading && sortedAlerts.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-soc-border bg-soc-panelSoft/40 p-4 text-sm text-soc-muted">
            No alerts yet. The stream will populate this queue when events arrive.
          </div>
        ) : null}

        {sortedAlerts.map((alert) => (
          <button
            type="button"
            key={`${alert.id}-${alert.timestamp}`}
            onClick={() => openUserModal(alert)}
            className={`w-full rounded-[22px] border p-4 text-left transition duration-200 hover:border-soc-electric/45 hover:bg-soc-panelSoft/90 ${
              alert.verdict === "HACKER"
                ? "soc-hacker-alert border-soc-red/50 bg-soc-red/10"
                : "border-soc-border/70 bg-soc-panelSoft/55"
            }`}
          >
            <div className="mb-3 flex items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                {alert.verdict === "HACKER" ? (
                  <div className="soc-threat-dot h-2.5 w-2.5 shrink-0" style={{ transform: "none" }}>
                    <span />
                  </div>
                ) : null}

                <span
                  className={`rounded-full border px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] ${
                    verdictTone[alert.verdict] || verdictTone.FORGETFUL_USER
                  }`}
                >
                  {String(alert.verdict || "UNKNOWN").replace(/_/g, " ")}
                </span>
              </div>
              <span className="text-[11px] text-soc-muted">{formatAlertTime(alert.timestamp)}</span>
            </div>

            <p className="text-sm text-soc-text">{alert.message}</p>
            <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-soc-muted">
              <span>{alert.userName}</span>
              <span>{alert.sourceIp}</span>
              <span>{alert.locationLabel}</span>
              <span>Score {formatAlertScore(alert.score)}%</span>
            </div>
          </button>
        ))}
      </div>
    </section>
  );
}
