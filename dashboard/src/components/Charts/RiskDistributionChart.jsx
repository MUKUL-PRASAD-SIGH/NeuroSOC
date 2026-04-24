import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

export default function RiskDistributionChart({ data }) {
  return (
    <section className="soc-glass h-[280px] p-4">
      <h3 className="mb-3 text-sm font-semibold uppercase tracking-[0.16em] text-soc-muted">Risk Score Distribution</h3>
      <ResponsiveContainer width="100%" height="88%">
        <BarChart data={data}>
          <CartesianGrid stroke="#23344f" strokeDasharray="4 4" />
          <XAxis dataKey="bucket" stroke="#7d8ba4" fontSize={12} />
          <YAxis stroke="#7d8ba4" fontSize={12} />
          <Tooltip
            contentStyle={{ background: "#101827dd", border: "1px solid #2e4464", color: "#d8e3f1", backdropFilter: "blur(10px)" }}
            labelStyle={{ color: "#d8e3f1" }}
          />
          <Bar dataKey="count" fill="#ffbe3d" radius={[8, 8, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </section>
  );
}
