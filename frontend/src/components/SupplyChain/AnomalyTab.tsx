import { useState } from "react";
import { ScatterChart, Scatter, XAxis, YAxis, ZAxis, ResponsiveContainer, Tooltip, CartesianGrid } from "recharts";
import { useAnomalyDetect } from "../../hooks/useSupplyChain";

const DEFAULT_VALUES = "10, 12, 11, 13, 9, 10, 12, 55, 11, 13, 12, 10, 9, 58, 11, 12, 13, 10, 9, 60, 11";

export default function AnomalyTab() {
  const mutation = useAnomalyDetect();
  const [valuesText, setValuesText] = useState(DEFAULT_VALUES);
  const [threshold, setThreshold] = useState("3.0");

  const data = mutation.data;

  function submit(e: React.FormEvent) {
    e.preventDefault();
    const values = valuesText.split(",").map((s) => Number(s.trim())).filter((n) => !Number.isNaN(n));
    if (values.length < 5) return;
    mutation.mutate({ values, threshold: Number(threshold) || 3.0 });
  }

  const anomalies = data?.anomalies ?? [];

  // Build scatter data from anomaly points (index, value)
  const scatterData = data && !data.error && data.anomalies
    ? data.anomalies.map((a) => ({ x: a.index, y: a.value }))
    : [];

  return (
    <div className="bg-surface border border-outline rounded-material-lg p-5">
      <h3 className="text-[15px] text-onsurface font-medium">🚨 Phát hiện bất thường (Anomaly Detection)</h3>
      <p className="text-[12px] text-onsurface-muted mt-0.5 mb-4">IsolationForest/MLflow hoặc modified z-score</p>

      <form onSubmit={submit} className="mb-5 space-y-3">
        <div>
          <label className="block text-[12px] text-onsurface-muted mb-1">Chuỗi giá trị (cách nhau bởi dấu phẩy)</label>
          <textarea value={valuesText} onChange={(e) => setValuesText(e.target.value)} rows={2}
            className="w-full px-3 py-2 border border-outline rounded-material text-[13px] font-mono focus:outline-none focus:border-google-blue" />
        </div>
        <div className="flex items-center gap-3">
          <label className="text-[12px] text-onsurface-muted">Ngưỡng</label>
          <input type="number" step="0.1" min={1} max={6} value={threshold} onChange={(e) => setThreshold(e.target.value)} className="w-20 px-3 py-2 border border-outline rounded-material text-[13px] focus:outline-none focus:border-google-blue" />
          <button type="submit" disabled={mutation.isPending} className="px-4 py-2 rounded-material bg-google-blue text-white text-[13px] font-medium hover:bg-google-blue/90 disabled:opacity-50">
            {mutation.isPending ? "Đang phân tích..." : "Phát hiện"}
          </button>
        </div>
      </form>

      {mutation.isError && <ErrorBox message="Không thể kết nối Supply Chain service." />}
      {data?.error && <ErrorBox message={String(data.error)} />}

      {data && !data.error && data.anomalies && (
        <div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
            <Metric label="Số điểm bất thường" value={String(data.count ?? anomalies.length)} />
            <Metric label="Ngưỡng" value={String(data.threshold ?? threshold)} />
            <Metric label="Phương pháp" value={shortMethod(data.method)} mono />
            <Metric label="Tổng điểm" value={String(countPoints(valuesText))} />
          </div>

          {scatterData.length === 0 && anomalies.length > 0 && (
            <div className="space-y-1.5 mb-4">
              {anomalies.slice(0, 10).map((a) => (
                <div key={a.index} className="flex items-center justify-between bg-red-50 rounded-material px-4 py-2 text-[13px]">
                  <span className="font-mono text-red-800">Điểm #{a.index}</span>
                  <span className="font-mono text-red-800 font-medium">{a.value}</span>
                  <span className="text-[12px] text-red-700">z={a.z?.toFixed(2) ?? a.score?.toFixed(2) ?? "—"}</span>
                </div>
              ))}
            </div>
          )}

          {scatterData.length > 0 && (
            <div className="h-56">
              <ResponsiveContainer width="100%" height="100%">
                <ScatterChart margin={{ top: 10, right: 12, bottom: 10, left: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#eee" />
                  <XAxis type="number" dataKey="x" name="index" tick={{ fontSize: 11 }} />
                  <YAxis type="number" dataKey="y" name="value" tick={{ fontSize: 11 }} />
                  <ZAxis range={[80, 80]} />
                  <Tooltip cursor={{ strokeDasharray: "3 3" }} />
                  <Scatter data={scatterData} fill="#e53935" />
                </ScatterChart>
              </ResponsiveContainer>
            </div>
          )}

          {anomalies.length === 0 && (
            <p className="text-[13px] text-google-green bg-google-green/10 rounded-material px-3 py-2">Không phát hiện bất thường nào.</p>
          )}
        </div>
      )}
    </div>
  );
}

function countPoints(text: string): number {
  return text.split(",").map((s) => Number(s.trim())).filter((n) => !Number.isNaN(n)).length;
}

function Metric({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="bg-surface-container rounded-material p-3">
      <p className="text-[11px] text-onsurface-muted">{label}</p>
      <p className={`text-[18px] text-onsurface font-medium mt-0.5 ${mono ? "font-mono text-[12px]" : ""}`}>{value}</p>
    </div>
  );
}

function shortMethod(m?: string): string {
  if (!m) return "—";
  return m.length > 22 ? m.slice(0, 22) + "…" : m;
}

function ErrorBox({ message }: { message: string }) {
  return <div className="px-3 py-2 rounded-material bg-red-50 text-red-700 text-[13px] mb-3">{message}</div>;
}