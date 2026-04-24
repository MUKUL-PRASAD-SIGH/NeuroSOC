import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const SERIES = [
  { key: "HACKER", color: "#ff4d5a" },
  { key: "FORGETFUL_USER", color: "#ffbe3d" },
  { key: "LEGITIMATE", color: "#19e6ff" },
];

export default function VerdictTimeline({ data }) {
  return (
    <section className="soc-glass rounded-[28px] p-4 md:p-5">
      <div className="mb-4 flex items-start justify-between gap-3">
        <div>
          <p className="soc-kicker">Verdict Timeline</p>
          <h2 className="mt-2 text-xl font-semibold text-soc-text">Classifier verdict flow</h2>
        </div>
        <div className="flex flex-wrap justify-end gap-2 text-[10px] font-semibold uppercase tracking-[0.18em] text-soc-muted">
          {SERIES.map((series) => (
            <span key={series.key} className="inline-flex items-center gap-2 rounded-full border border-soc-border/80 bg-soc-panelSoft/55 px-3 py-1">
              <span className="h-2 w-2 rounded-full" style={{ backgroundColor: series.color }} />
              {series.key.replace("_", " ")}
            </span>
          ))}
        </div>
      </div>

      <div className="h-[360px]">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data}>
            <defs>
              {SERIES.map((series) => (
                <linearGradient key={series.key} id={`gradient-${series.key}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={series.color} stopOpacity={0.35} />
                  <stop offset="100%" stopColor={series.color} stopOpacity={0} />
                </linearGradient>
              ))}
            </defs>
            <CartesianGrid stroke="rgba(94, 120, 163, 0.16)" vertical={false} />
            <XAxis
              dataKey="time"
              tickFormatter={(value) =>
                new Date(value).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
              }
              stroke="#7d90b8"
              tickLine={false}
              axisLine={false}
            />
            <YAxis allowDecimals={false} stroke="#7d90b8" tickLine={false} axisLine={false} />
            <Tooltip
              contentStyle={{
                background: "rgba(11, 18, 34, 0.96)",
                border: "1px solid rgba(48, 67, 104, 0.9)",
                borderRadius: "16px",
                color: "#dce7ff",
              }}
              labelFormatter={(value) => new Date(value).toLocaleString()}
            />
            {SERIES.map((series) => (
              <Area
                key={series.key}
                type="monotone"
                dataKey={series.key}
                stroke={series.color}
                fill={`url(#gradient-${series.key})`}
                strokeWidth={2}
              />
            ))}
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}
