import { useMemo, useState } from "react";
import { useDashboardStore } from "../store/dashboardStore";

const verdictTone = {
  HACKER: "border-soc-red/50 bg-soc-red/12 text-soc-red",
  FORGETFUL_USER: "border-soc-amber/50 bg-soc-amber/12 text-soc-amber",
  LEGITIMATE: "border-soc-green/45 bg-soc-green/12 text-soc-green",
  INCONCLUSIVE: "border-soc-border bg-soc-panelSoft/40 text-soc-muted",
};

const verdictEmoji = {
  HACKER: "🔴",
  FORGETFUL_USER: "🟠",
  LEGITIMATE: "🟢",
  INCONCLUSIVE: "⚪",
};

const verdictLabel = {
  HACKER: "Threat Detected",
  FORGETFUL_USER: "Suspicious — Likely Confused User",
  LEGITIMATE: "Normal Activity",
  INCONCLUSIVE: "Monitoring",
};

const verdictSummary = {
  HACKER: (a) =>
    `A session from ${a.sourceIp} (${a.locationLabel}) was flagged as a likely attacker with ${Math.round(a.score * 100)}% confidence. The system has engaged automated response.`,
  FORGETFUL_USER: (a) =>
    `${a.userName || a.sourceIp} showed unusual behaviour (${Math.round(a.score * 100)}% risk) but did not match a full attack pattern. Likely a confused or locked-out user.`,
  LEGITIMATE: (a) =>
    `Session from ${a.userName || a.sourceIp} passed all checks. Risk score ${Math.round(a.score * 100)}% — no action needed.`,
  INCONCLUSIVE: (a) =>
    `Not enough signal yet for ${a.sourceIp}. Session is being monitored (score ${Math.round(a.score * 100)}%).`,
};

const ALERT_CAP = 50;

function formatAlertTime(timestamp) {
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) return "--:--";
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function AlertCard({ alert, onOpen }) {
  const [showRaw, setShowRaw] = useState(false);
  const verdict = alert.verdict || "INCONCLUSIVE";
  const summary = (verdictSummary[verdict] || verdictSummary.INCONCLUSIVE)(alert);

  return (
    <div
      className={`rounded-[22px] border p-4 transition duration-200 ${
        verdict === "HACKER"
          ? "soc-hacker-alert border-soc-red/50 bg-soc-red/10"
          : "border-soc-border/70 bg-soc-panelSoft/55"
      }`}
    >
      {/* Header row */}
      <div className="mb-2 flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          {verdict === "HACKER" && (
            <div className="soc-threat-dot h-2.5 w-2.5 shrink-0" style={{ transform: "none" }}>
              <span />
            </div>
          )}
          <span
            className={`rounded-full border px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] ${
              verdictTone[verdict] || verdictTone.INCONCLUSIVE
            }`}
          >
            {verdictEmoji[verdict]} {verdictLabel[verdict] || verdict.replace(/_/g, " ")}
          </span>
        </div>
        <span className="text-[11px] text-soc-muted">{formatAlertTime(alert.timestamp)}</span>
      </div>

      {/* Human summary */}
      {!showRaw && (
        <p className="text-sm leading-relaxed text-soc-text">{summary}</p>
      )}

      {/* Raw JSON view */}
      {showRaw && (
        <pre className="mt-2 max-h-48 overflow-auto rounded-xl bg-soc-panel/80 p-3 text-[11px] leading-relaxed text-soc-muted">
          {JSON.stringify(alert, null, 2)}
        </pre>
      )}

      {/* Footer */}
      <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap gap-x-3 gap-y-1 text-xs text-soc-muted">
          <span>{alert.sourceIp}</span>
          <span>{alert.locationLabel}</span>
          <span>Risk {Math.round((alert.score || 0) * 100)}%</span>
          {alert.modelVersion && <span>Model {alert.modelVersion}</span>}
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => setShowRaw((v) => !v)}
            className="rounded-full border border-soc-border/60 bg-soc-panelSoft/40 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.14em] text-soc-muted transition hover:border-soc-electric/40 hover:text-soc-text"
          >
            {showRaw ? "Human" : "Raw"}
          </button>
          <button
            type="button"
            onClick={() => onOpen(alert)}
            className="rounded-full border border-soc-electric/30 bg-soc-electric/10 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.14em] text-soc-electric transition hover:bg-soc-electric/20"
          >
            Details
          </button>
        </div>
      </div>
    </div>
  );
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
      {showHeader && (
        <div className="mb-4 flex items-center justify-between gap-3">
          <div>
            <p className="soc-kicker">Alert Feed</p>
            <h2 className="mt-2 text-xl font-semibold text-soc-text">Live analyst queue</h2>
          </div>
          <span className="rounded-full border border-soc-electric/30 bg-soc-electric/10 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-soc-electric">
            {loading ? "Hydrating" : status || "Idle"}
          </span>
        </div>
      )}

      <div className="flex-1 max-h-[500px] space-y-3 overflow-y-auto pr-1">
        {!loading && sortedAlerts.length === 0 && (
          <div className="rounded-2xl border border-dashed border-soc-border bg-soc-panelSoft/40 p-4 text-sm text-soc-muted">
            No alerts yet. The stream will populate this queue when events arrive.
          </div>
        )}
        {sortedAlerts.map((alert) => (
          <AlertCard
            key={`${alert.id}-${alert.timestamp}`}
            alert={alert}
            onOpen={openUserModal}
          />
        ))}
      </div>
    </section>
  );
}
