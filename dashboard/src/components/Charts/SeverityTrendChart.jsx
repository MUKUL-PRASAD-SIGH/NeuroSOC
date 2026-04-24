import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

export default function SeverityTrendChart({ data }) {
  return (
    <section className="soc-glass h-[280px] p-4">
      <h3 className="mb-3 text-sm font-semibold uppercase tracking-[0.16em] text-soc-muted">Alert Severity Trend</h3>
      <ResponsiveContainer width="100%" height="88%">
        <AreaChart data={data}>
          <CartesianGrid stroke="#23344f" strokeDasharray="4 4" />
          <XAxis dataKey="time" stroke="#7d8ba4" fontSize={12} />
          <YAxis stroke="#7d8ba4" fontSize={12} />
          <Tooltip
            contentStyle={{ background: "#101827dd", border: "1px solid #2e4464", color: "#d8e3f1", backdropFilter: "blur(10px)" }}
            labelStyle={{ color: "#d8e3f1" }}
          />
          <Area type="monotone" dataKey="high" stroke="#ff4d5a" fill="#ff4d5a3d" strokeWidth={2.2} />
        </AreaChart>
      </ResponsiveContainer>
    </section>
  );
}
