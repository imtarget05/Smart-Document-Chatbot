import { useState } from "react";
import { LineChart, Line, XAxis, YAxis, ResponsiveContainer, CartesianGrid, Tooltip } from "recharts";
import { useForecast } from "../../hooks/useSupplyChain";
import type { ForecastResponse } from "../../services/supplyChainApi";

const DEFAULT_HISTORY = [50, 52, 49, 55, 58, 56, 60, 62, 59, 57, 63, 66, 64, 68, 70];

export default function ForecastTab() {
  const mutation = useForecast();
  const [historyText, setHistoryText] = useState(DEFAULT_HISTORY.join(","));
  const [periods, setPeriods] = useState("30");

  const data = mutation.data;

  function submit(e: React.FormEvent) {
    e.preventDefault();
    const history = historyText
      .split(",")
      .map((s) => Number(s.trim()))
      .filter((n) => !Number.isNaN(n));
    if (history.length === 0) return;
    mutation.mutate({ history, periods: Number(periods) || 30 });
  }

  return (
    <Card title="📈 Dự báo nhu cầu (Demand Forecast)" subtitle="Prophet/MLflow hoặc linear trend weekly seasonal">
      <form onSubmit={submit} className="mb-4 space-y-3">
        <div>
          <label className="block text-[12px] text-onsurface-muted mb-1">Chuỗi lịch sử (cách nhau bởi dấu phẩy)</label>
          <input
            value={historyText}
            onChange={(e) => setHistoryText(e.target.value)}
            className="w-full px-3 py-2 border border-outline rounded-material text-[13px] font-mono focus:outline-none focus:border-google-blue"
          />
        </div>
        <div className="flex items-center gap-3">
          <label className="text-[12px] text-onsurface-muted">Số kỳ dự báo</label>
          <input
            type="number"
            min={1}
            max={90}
            value={periods}
            onChange={(e) => setPeriods(e.target.value)}
            className="w-24 px-3 py-2 border border-outline rounded-material text-[13px] focus:outline-none focus:border-google-blue"
          />
          <button
            type="submit"
            disabled={mutation.isPending}
            className="px-4 py-2 rounded-material bg-google-blue text-white text-[13px] font-medium hover:bg-google-blue/90 disabled:opacity-50"
          >
            {mutation.isPending ? "Đang tính..." : "Dự báo"}
          </button>
        </div>
      </form>

      {mutation.isError && <ErrorBox message="Không thể kết nối Supply Chain service." />}
      {data?.error && <ErrorBox message={data.error} />}

      {data && !data.error && Array.isArray(data.forecast) && data.forecast.length > 0 && (
        <ForecastResult data={data} />
      )}
    </Card>
  );
}

function ForecastResult({ data }: { data: ForecastResponse }) {
  const points = data.forecast ?? [];
  const chartData = points.map((v, i) => ({ label: `K${i + 1}`, value: v }));
  return (
    <div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
        <Metric label="Số điểm dự báo" value={String(points.length)} />
        <Metric label="Phương pháp" value={data.method ?? "—"} mono />
        <Metric label="Điểm history" value={String(data.history_points ?? 0)} />
        {data.trend_per_period !== undefined && (
          <Metric label="Xu hướng/kỳ" value={formatNum(data.trend_per_period)} />
        )}
      </div>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData} margin={{ top: 8, right: 12, bottom: 8, left: -12 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#eee" />
            <XAxis dataKey="label" tick={{ fontSize: 11 }} />
            <YAxis tick={{ fontSize: 11 }} />
            <Tooltip />
            <Line type="monotone" dataKey="value" name="Dự báo" stroke="#1a73e8" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function formatNum(n: number): string {
  return Number.isInteger(n) ? String(n) : n.toFixed(2);
}

// Shared helpers (kept local to this file to avoid coupling)
function Card({ title, subtitle, children }: { title: string; subtitle?: string; children: React.ReactNode }) {
  return (
    <div className="bg-surface border border-outline rounded-material-lg p-5">
      <h3 className="text-[15px] text-onsurface font-medium">{title}</h3>
      {subtitle && <p className="text-[12px] text-onsurface-muted mt-0.5 mb-4">{subtitle}</p>}
      <div className="pt-1">{children}</div>
    </div>
  );
}

function Metric({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="bg-surface-container rounded-material p-3">
      <p className="text-[11px] text-onsurface-muted">{label}</p>
      <p className={`text-[18px] text-onsurface font-medium mt-0.5 ${mono ? "font-mono text-[13px]" : ""}`}>{value}</p>
    </div>
  );
}

function ErrorBox({ message }: { message: string }) {
  return (
    <div className="px-3 py-2 rounded-material bg-red-50 text-red-700 text-[13px]">{message}</div>
  );
}