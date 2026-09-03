import { useState } from "react";
import { useOptimizeRoute } from "../../hooks/useSupplyChain";

const DEFAULT_MATRIX = [
  [0, 10, 15, 20],
  [10, 0, 35, 25],
  [15, 35, 0, 30],
  [20, 25, 30, 0],
];

export default function RouteTab() {
  const mutation = useOptimizeRoute();
  const [matrixText, setMatrixText] = useState(DEFAULT_MATRIX.map((r) => r.join(",")).join(";"));
  const [vehicles, setVehicles] = useState("1");

  const data = mutation.data;

  function submit(e: React.FormEvent) {
    e.preventDefault();
    const rows = matrixText.split(";").map((r) => r.split(",").map((s) => Number(s.trim())).filter((n) => !Number.isNaN(n))).filter((r) => r.length > 0);
    if (rows.length < 2) return;
    mutation.mutate({ distance_matrix: rows, num_vehicles: Number(vehicles) || 1, depot: 0 });
  }

  return (
    <div className="bg-surface border border-outline rounded-material-lg p-5">
      <h3 className="text-[15px] text-onsurface font-medium">🚚 Tối ưu tuyến đường (VRP)</h3>
      <p className="text-[12px] text-onsurface-muted mt-0.5 mb-4">OR-Tools hoặc nearest-neighbor + 2-opt. Ma trận cách hàng bởi dấu ;</p>

      <form onSubmit={submit} className="mb-5 space-y-3">
        <div>
          <label className="block text-[12px] text-onsurface-muted mb-1">Ma trận khoảng cách</label>
          <textarea value={matrixText} onChange={(e) => setMatrixText(e.target.value)} rows={4}
            className="w-full px-3 py-2 border border-outline rounded-material text-[13px] font-mono focus:outline-none focus:border-google-blue" />
        </div>
        <div className="flex items-center gap-3">
          <label className="text-[12px] text-onsurface-muted">Số xe</label>
          <input type="number" min={1} max={5} value={vehicles} onChange={(e) => setVehicles(e.target.value)} className="w-20 px-3 py-2 border border-outline rounded-material text-[13px] focus:outline-none focus:border-google-blue" />
          <button type="submit" disabled={mutation.isPending} className="px-4 py-2 rounded-material bg-google-blue text-white text-[13px] font-medium hover:bg-google-blue/90 disabled:opacity-50">
            {mutation.isPending ? "Đang tối ưu..." : "Tối ưu"}
          </button>
        </div>
      </form>

      {mutation.isError && <ErrorBox message="Không thể kết nối Supply Chain service." />}
      {data?.error && <ErrorBox message={String(data.error)} />}

      {data && !data.error && Array.isArray(data.routes) && data.routes.length > 0 && (
        <div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-4">
            <RouteMetric label="Tổng quãng đường" value={`${data.total_distance?.toFixed(2) ?? 0}`} unit="km" />
            <RouteMetric label="Số tuyến" value={String(data.routes.length)} />
            <RouteMetric label="Phương pháp" value={shortMethod(data.method)} mono />
          </div>
          <div className="space-y-2">
            {data.routes.map((route, i) => (
              <div key={i} className="flex items-center justify-between bg-surface-container rounded-material px-4 py-2.5">
                <div className="flex items-center gap-2">
                  <span className="text-[11px] text-onsurface-muted w-16">Xe {i + 1}</span>
                  <span className="font-mono text-[13px] text-onsurface">{route.stops.join(" → ")}</span>
                </div>
                <span className="text-[12px] text-onsurface-muted">{route.distance.toFixed(2)} km</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function RouteMetric({ label, value, unit, mono }: { label: string; value: string; unit?: string; mono?: boolean }) {
  return (
    <div className="bg-surface-container rounded-material p-3">
      <p className="text-[11px] text-onsurface-muted">{label}</p>
      <p className={`text-[18px] text-onsurface font-medium mt-0.5 ${mono ? "font-mono text-[12px]" : ""}`}>{value}{unit ? ` ${unit}` : ""}</p>
    </div>
  );
}

function shortMethod(m?: string): string {
  if (!m) return "—";
  return m.length > 18 ? m.slice(0, 18) + "…" : m;
}

function ErrorBox({ message }: { message: string }) {
  return <div className="px-3 py-2 rounded-material bg-red-50 text-red-700 text-[13px] mb-3">{message}</div>;
}