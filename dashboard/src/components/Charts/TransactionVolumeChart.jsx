import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export default function TransactionVolumeChart({ data }) {
  return (
    <section className="soc-glass h-[280px] p-4">
      <h3 className="mb-3 text-sm font-semibold uppercase tracking-[0.16em] text-soc-muted">Transaction Volume</h3>
      <ResponsiveContainer width="100%" height="88%">
        <LineChart data={data}>
          <CartesianGrid stroke="#23344f" strokeDasharray="4 4" />
          <XAxis dataKey="time" stroke="#7d8ba4" fontSize={12} />
          <YAxis stroke="#7d8ba4" fontSize={12} />
          <Tooltip
            contentStyle={{ background: "#101827dd", border: "1px solid #2e4464", color: "#d8e3f1", backdropFilter: "blur(10px)" }}
            labelStyle={{ color: "#d8e3f1" }}
          />
          <Line type="monotone" dataKey="transactions" stroke="#11d6ff" strokeWidth={2.4} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </section>
  );
}
