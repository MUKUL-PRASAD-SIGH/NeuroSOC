import { useState } from "react";
import {
  PolarAngleAxis,
  PolarGrid,
  Radar,
  RadarChart,
  ResponsiveContainer,
} from "recharts";
import { useDashboardStore } from "../store/dashboardStore";

const verdictTone = {
  HACKER: "text-soc-red",
  FORGETFUL_USER: "text-soc-amber",
  LEGITIMATE: "text-soc-green",
  INCONCLUSIVE: "text-soc-muted",
};

const verdictBadge = {
  HACKER: "border-soc-red/50 bg-soc-red/12 text-soc-red",
  FORGETFUL_USER: "border-soc-amber/50 bg-soc-amber/12 text-soc-amber",
  LEGITIMATE: "border-soc-green/45 bg-soc-green/12 text-soc-green",
  INCONCLUSIVE: "border-soc-border bg-soc-panelSoft/40 text-soc-muted",
};

const verdictHeadline = {
  HACKER: "🔴 Threat Confirmed",
  FORGETFUL_USER: "🟠 Suspicious — Likely Confused User",
  LEGITIMATE: "🟢 Normal Activity",
  INCONCLUSIVE: "⚪ Insufficient Signal",
};

const verdictExplain = {
  HACKER: (a) =>
    `This session was classified as a likely attacker with ${Math.round((a.score || 0) * 100)}% confidence. ` +
    `The SNN detected an anomalous spike pattern, the LNN found no matching behavioural history, ` +
    `and XGBoost classified the traffic as ${a.raw?.xgb_class || "malicious"}. ` +
    `Automated response has been engaged — the session was diverted to a sandbox.`,
  FORGETFUL_USER: (a) =>
    `This session raised flags (${Math.round((a.score || 0) * 100)}% risk) but did not reach the attacker threshold. ` +
    `The pattern is consistent with a confused or locked-out user — repeated failures, known device, ` +
    `behaviour that stopped when challenged. No automated block was applied. ` +
    `Analyst review is recommended before restoring access.`,
  LEGITIMATE: (a) =>
    `All checks passed for this session (risk score ${Math.round((a.score || 0) * 100)}%). ` +
    `The SNN found no spike anomalies, the LNN matched the user's stored behavioural baseline, ` +
    `and XGBoost returned ${a.raw?.xgb_class || "BENIGN"}. No action required.`,
  INCONCLUSIVE: (a) =>
    `Not enough signal to make a confident decision (score ${Math.round((a.score || 0) * 100)}%). ` +
    `The session is being monitored. Further activity will update this verdict automatically.`,
};

function ModelBreakdown({ raw }) {
  if (!raw) return null;
  const rows = [
    {
      label: "SNN Spike Score",
      value: `${Math.round((raw.snn_score || 0) * 100)}%`,
      note: raw.snn_score > 0.5 ? "Anomalous burst detected" : "No spike anomaly",
      bad: raw.snn_score > 0.5,
    },
    {
      label: "LNN Behaviour Class",
      value: raw.lnn_class || "—",
      note: raw.lnn_class === "BENIGN" ? "Matches known profile" : "Deviates from baseline",
      bad: raw.lnn_class !== "BENIGN",
    },
    {
      label: "XGBoost Traffic Class",
      value: raw.xgb_class || "—",
      note: raw.xgb_class === "BENIGN" ? "Normal traffic pattern" : "Flagged traffic type",
      bad: raw.xgb_class !== "BENIGN",
    },
    {
      label: "Behavioural Drift",
      value: `${Math.round((raw.behavioral_delta || 0) * 100)}%`,
      note: raw.behavioral_delta > 0.3 ? "High drift from user baseline" : "Within normal range",
      bad: raw.behavioral_delta > 0.3,
    },
    {
      label: "Final Confidence",
      value: `${Math.round((raw.confidence || 0) * 100)}%`,
      note: "Weighted fusion of all three models",
      bad: false,
    },
  ];

  return (
    <div className="mt-4 space-y-2">
      {rows.map((row) => (
        <div
          key={row.label}
          className="flex items-center justify-between rounded-xl border border-soc-border/60 bg-soc-panel/50 px-3 py-2"
        >
          <div>
            <p className="text-xs font-semibold text-soc-text">{row.label}</p>
            <p className="text-[11px] text-soc-muted">{row.note}</p>
          </div>
          <span
            className={`rounded-full px-2.5 py-1 text-[11px] font-semibold ${
              row.bad
                ? "bg-soc-red/15 text-soc-red"
                : "bg-soc-green/15 text-soc-green"
            }`}
          >
            {row.value}
          </span>
        </div>
      ))}
    </div>
  );
}

function VerdictHistory({ recentVerdicts }) {
  if (!recentVerdicts?.length) return null;
  return (
    <div className="mt-4 space-y-2">
      {recentVerdicts.map((item, i) => (
        <div
          key={item.id || i}
          className="flex items-center justify-between rounded-xl border border-soc-border/60 bg-soc-panel/50 px-3 py-2"
        >
          <div className="flex items-center gap-2">
            <span className={`text-sm font-semibold ${verdictTone[item.verdict] || "text-soc-muted"}`}>
              {item.verdict?.replace(/_/g, " ") || "UNKNOWN"}
            </span>
            <span className="text-[11px] text-soc-muted">
              {new Date(item.timestamp).toLocaleString([], {
                month: "short",
                day: "numeric",
                hour: "2-digit",
                minute: "2-digit",
              })}
            </span>
          </div>
          <span className="text-xs text-soc-muted">
            {Math.round((item.score || 0) * 100)}% risk
          </span>
        </div>
      ))}
    </div>
  );
}

export default function UserProfileModal() {
  const modal = useDashboardStore((state) => state.modal);
  const closeUserModal = useDashboardStore((state) => state.closeUserModal);
  const [showRaw, setShowRaw] = useState(false);
  const alert = modal.selectedAlert;

  if (!modal.open || !alert) return null;

  const verdict = alert.verdict || "INCONCLUSIVE";
  const explain = (verdictExplain[verdict] || verdictExplain.INCONCLUSIVE)(alert);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm">
      <div className="soc-glass max-h-[92vh] w-full max-w-5xl overflow-y-auto p-5 md:p-6">

        {/* Header */}
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="soc-kicker">Session Analysis</p>
            <h2 className="mt-2 text-2xl font-semibold text-soc-text">
              {alert.userName || alert.userId || alert.sourceIp}
            </h2>
            <p className="mt-1 text-sm text-soc-muted">
              {alert.sourceIp} · {alert.locationLabel}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setShowRaw((v) => !v)}
              className="rounded-full border border-soc-border/60 bg-soc-panelSoft/40 px-3 py-2 text-xs font-semibold uppercase tracking-[0.18em] text-soc-muted transition hover:border-soc-electric/40 hover:text-soc-text"
            >
              {showRaw ? "Human View" : "Raw JSON"}
            </button>
            <button
              type="button"
              onClick={closeUserModal}
              className="rounded-full border border-soc-border/80 bg-soc-panelSoft/60 px-3 py-2 text-xs font-semibold uppercase tracking-[0.18em] text-soc-muted transition hover:border-soc-electric/40 hover:text-soc-text"
            >
              Close
            </button>
          </div>
        </div>

        {/* Raw JSON mode */}
        {showRaw ? (
          <pre className="mt-5 max-h-[60vh] overflow-auto rounded-2xl border border-soc-border/60 bg-soc-panel/80 p-4 text-[11px] leading-relaxed text-soc-muted">
            {JSON.stringify(alert, null, 2)}
          </pre>
        ) : (
          <>
            {/* Verdict summary banner */}
            <div className="mt-5 rounded-2xl border border-soc-border/60 bg-soc-panelSoft/55 p-4">
              <div className="flex items-center gap-3">
                <span
                  className={`rounded-full border px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] ${
                    verdictBadge[verdict] || verdictBadge.INCONCLUSIVE
                  }`}
                >
                  {verdictHeadline[verdict] || verdict.replace(/_/g, " ")}
                </span>
                <span className="text-sm text-soc-muted">
                  Risk score: <span className="font-semibold text-soc-text">{Math.round((alert.score || 0) * 100)}%</span>
                </span>
                {alert.modelVersion && (
                  <span className="text-xs text-soc-muted">Model: {alert.modelVersion}</span>
                )}
              </div>
              <p className="mt-3 text-sm leading-relaxed text-soc-text">{explain}</p>
            </div>

            <div className="mt-5 grid gap-5 xl:grid-cols-[1.25fr_0.95fr]">

              {/* Left — radar + model breakdown */}
              <section className="rounded-[24px] border border-soc-border/80 bg-soc-panelSoft/55 p-4">
                <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-soc-muted">
                  Behavioural Signal Radar
                </p>
                <p className="mt-1 text-xs text-soc-muted">
                  Each axis is a normalised signal extracted from the session. Higher = more anomalous.
                </p>
                <div className="mt-3 h-[300px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <RadarChart data={alert.dimensions}>
                      <PolarGrid stroke="rgba(94, 120, 163, 0.2)" />
                      <PolarAngleAxis dataKey="subject" tick={{ fill: "#8ea2c9", fontSize: 10 }} />
                      <Radar
                        name="Behavior"
                        dataKey="value"
                        stroke="#19e6ff"
                        fill="#19e6ff"
                        fillOpacity={0.3}
                      />
                    </RadarChart>
                  </ResponsiveContainer>
                </div>

                <p className="mt-4 text-[10px] font-semibold uppercase tracking-[0.22em] text-soc-muted">
                  Model Breakdown
                </p>
                <ModelBreakdown raw={alert.raw} />
              </section>

              {/* Right — verdict history */}
              <section className="rounded-[24px] border border-soc-border/80 bg-soc-panelSoft/55 p-4">
                <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-soc-muted">
                  Recent Session History
                </p>
                <p className="mt-1 text-xs text-soc-muted">
                  Last {alert.recentVerdicts?.length || 0} verdicts for this user.
                </p>
                {alert.recentVerdicts?.length ? (
                  <VerdictHistory recentVerdicts={alert.recentVerdicts} />
                ) : (
                  <p className="mt-4 text-sm text-soc-muted">No history available for this session.</p>
                )}
              </section>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
