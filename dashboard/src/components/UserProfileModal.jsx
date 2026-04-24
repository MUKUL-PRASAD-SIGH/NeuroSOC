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
};

export default function UserProfileModal() {
  const modal = useDashboardStore((state) => state.modal);
  const closeUserModal = useDashboardStore((state) => state.closeUserModal);
  const alert = modal.selectedAlert;

  if (!modal.open || !alert) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm">
      <div className="soc-glass max-h-[92vh] w-full max-w-5xl overflow-y-auto rounded-[28px] p-5 md:p-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="soc-kicker">User Profile</p>
            <h2 className="mt-2 text-2xl font-semibold text-soc-text">{alert.userName}</h2>
            <p className="mt-1 text-sm text-soc-muted">
              {alert.userId} · {alert.sourceIp} · {alert.locationLabel}
            </p>
          </div>
          <button
            type="button"
            onClick={closeUserModal}
            className="rounded-full border border-soc-border/80 bg-soc-panelSoft/60 px-3 py-2 text-xs font-semibold uppercase tracking-[0.18em] text-soc-muted transition hover:border-soc-electric/40 hover:text-soc-text"
          >
            Close
          </button>
        </div>

        <div className="mt-5 grid gap-5 xl:grid-cols-[1.25fr_0.95fr]">
          <section className="rounded-[24px] border border-soc-border/80 bg-soc-panelSoft/55 p-4">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-soc-muted">
                  Behavioral Dimensions
                </p>
                <p className="mt-2 text-sm text-soc-text">
                  Latest verdict: <span className={verdictTone[alert.verdict]}>{alert.verdict}</span>
                </p>
              </div>
              <span className="rounded-full border border-soc-red/30 bg-soc-red/10 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-soc-red">
                Score {Math.round(alert.score * 100)}%
              </span>
            </div>

            <div className="mt-4 h-[380px]">
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart data={alert.dimensions}>
                  <PolarGrid stroke="rgba(94, 120, 163, 0.2)" />
                  <PolarAngleAxis dataKey="subject" tick={{ fill: "#8ea2c9", fontSize: 11 }} />
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
          </section>

          <section className="rounded-[24px] border border-soc-border/80 bg-soc-panelSoft/55 p-4">
            <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-soc-muted">Last 10 Verdicts</p>
            <div className="mt-4 space-y-3">
              {alert.recentVerdicts.map((item) => (
                <article key={item.id} className="rounded-2xl border border-soc-border/70 bg-soc-panel/60 p-3">
                  <div className="flex items-center justify-between gap-3">
                    <span className={`text-sm font-semibold ${verdictTone[item.verdict]}`}>{item.verdict}</span>
                    <span className="text-xs text-soc-muted">{new Date(item.timestamp).toLocaleString()}</span>
                  </div>
                  <p className="mt-2 text-xs text-soc-muted">Confidence {Math.round(item.score * 100)}%</p>
                </article>
              ))}
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
