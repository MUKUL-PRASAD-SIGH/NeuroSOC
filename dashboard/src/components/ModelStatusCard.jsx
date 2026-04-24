import { useDashboardStore } from "../store/dashboardStore";

export default function ModelStatusCard() {
  const modelStatus = useDashboardStore((state) => state.modelStatus);
  const { data, loading, error, lastUpdated } = modelStatus;

  return (
    <section className="soc-glass rounded-[24px] p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="soc-kicker">Model Status</p>
          <h2 className="mt-2 text-lg font-semibold text-soc-text">Current inference stack</h2>
        </div>
        <span className="rounded-full border border-soc-electric/30 bg-soc-electric/10 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.2em] text-soc-electric">
          {loading ? "Syncing" : "60s Refresh"}
        </span>
      </div>

      {error ? <p className="mt-4 text-sm text-soc-red">{error}</p> : null}

      <div className="mt-4 grid gap-4 lg:grid-cols-[1.3fr_1fr]">
        <div className="space-y-3">
          {data.versions.map((version) => (
            <div key={version.label} className="rounded-2xl border border-soc-border/80 bg-soc-panelSoft/55 p-3">
              <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-soc-muted">{version.label}</p>
              <p className="mt-2 font-mono text-sm text-soc-text">{version.value}</p>
            </div>
          ))}
        </div>

        <div className="rounded-2xl border border-soc-border/80 bg-soc-panelSoft/55 p-3">
          <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-soc-muted">Validation F1</p>
          <div className="mt-3 space-y-3">
            {data.validationF1.map((entry) => (
              <div key={entry.label}>
                <div className="mb-1 flex items-center justify-between text-xs text-soc-muted">
                  <span>{entry.label}</span>
                  <span>{entry.value.toFixed(2)}</span>
                </div>
                <div className="h-2 rounded-full bg-soc-panel">
                  <div
                    className="h-2 rounded-full bg-gradient-to-r from-soc-electric via-soc-green to-soc-green"
                    style={{ width: `${Math.max(entry.value * 100, 6)}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
          <p className="mt-4 text-xs text-soc-muted">
            Last retrained:{" "}
            {data.lastRetrainedAt ? new Date(data.lastRetrainedAt).toLocaleString() : "Pending"}
          </p>
          <p className="mt-1 text-xs text-soc-muted">
            Last checked: {lastUpdated ? new Date(lastUpdated).toLocaleTimeString() : "Pending"}
          </p>
        </div>
      </div>
    </section>
  );
}
