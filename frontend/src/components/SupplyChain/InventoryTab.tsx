import { useState } from "react";
import { useInventoryOptimalOrder } from "../../hooks/useSupplyChain";

export default function InventoryTab() {
  const mutation = useInventoryOptimalOrder();
  const [yearlyDemand, setYearlyDemand] = useState("12000");
  const [orderCost, setOrderCost] = useState("50");
  const [holdingCost, setHoldingCost] = useState("5");
  const [stdDemand, setStdDemand] = useState("120");
  const [leadTime, setLeadTime] = useState("7");
  const [serviceLevel, setServiceLevel] = useState("0.95");

  const data = mutation.data;

  function submit(e: React.FormEvent) {
    e.preventDefault();
    mutation.mutate({
      annual_demand: Number(yearlyDemand) || 0,
      order_cost: Number(orderCost) || 0,
      holding_cost: Number(holdingCost) || 0,
      std_demand: Number(stdDemand) || 0,
      lead_time_days: Number(leadTime) || 1,
      service_level: Number(serviceLevel) || 0.95,
    });
  }

  return (
    <div className="bg-surface border border-outline rounded-material-lg p-5">
      <h3 className="text-[15px] text-onsurface font-medium">📦 Tối ưu tồn kho (EOQ / Safety Stock / Reorder Point)</h3>
      <p className="text-[12px] text-onsurface-muted mt-0.5 mb-4">EOQ + safety stock + reorder point</p>

      <form onSubmit={submit} className="mb-5 space-y-3">
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          <NumField label="Nhu cầu năm" value={yearlyDemand} onChange={setYearlyDemand} />
          <NumField label="Chi phí đặt hàng" value={orderCost} onChange={setOrderCost} />
          <NumField label="Chi phí lưu kho/đv" value={holdingCost} onChange={setHoldingCost} />
          <NumField label="σ nhu cầu ngày" value={stdDemand} onChange={setStdDemand} />
          <NumField label="Lead time (ngày)" value={leadTime} onChange={setLeadTime} />
          <NumField label="Service level (z)" value={serviceLevel} onChange={setServiceLevel} step="0.01" />
        </div>
        <button type="submit" disabled={mutation.isPending} className="px-4 py-2 rounded-material bg-google-blue text-white text-[13px] font-medium hover:bg-google-blue/90 disabled:opacity-50">
          {mutation.isPending ? "Đang tính..." : "Tính toán"}
        </button>
      </form>

      {mutation.isError && <ErrorBox message="Không thể kết nối Supply Chain service." />}
      {data?.error && <ErrorBox message={String(data.error)} />}

      {data && !data.error && data.eoq !== undefined && (
        <div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
            <Metric label="EOQ (đơn hàng tối ưu)" value={data.eoq.toFixed(1)} unit="đv" highlight />
            <Metric label="Safety stock" value={data.safety_stock?.toFixed(1) ?? "0.0"} unit="đv" />
            <Metric label="Reorder point" value={data.reorder_point?.toFixed(1) ?? "0.0"} unit="đv" />
            <Metric label="Nhu cầu ngày" value={data.daily_demand?.toFixed(2) ?? "0.00"} unit="đv/ngày" />
          </div>
          <div className="flex flex-wrap gap-3 justify-between items-end">
            <div className="text-[12px] text-onsurface-muted">
              <p>Service level: <span className="text-onsurface font-medium">{Math.round(Number(data.service_level ?? serviceLevel) * 100)}%</span></p>
              <p>Z-score: <span className="text-onsurface font-medium">{data.z_score ?? zFor(data.service_level ?? 0.95)}</span></p>
            </div>
            {data.method && <p className="text-[11px] text-onsurface-muted">Phương pháp: {data.method}</p>}
          </div>
        </div>
      )}
    </div>
  );
}

function NumField({ label, value, onChange, step = "1" }: { label: string; value: string; onChange: (v: string) => void; step?: string }) {
  return (
    <div>
      <label className="block text-[12px] text-onsurface-muted mb-1">{label}</label>
      <input type="number" step={step} value={value} onChange={(e) => onChange(e.target.value)} className="w-full px-3 py-2 border border-outline rounded-material text-[13px] font-mono focus:outline-none focus:border-google-blue" />
    </div>
  );
}

function Metric({ label, value, unit, highlight }: { label: string; value: string; unit?: string; highlight?: boolean }) {
  return (
    <div className={`rounded-material p-3 ${highlight ? "bg-google-blue/10 border border-google-blue/20" : "bg-surface-container"}`}>
      <p className="text-[11px] text-onsurface-muted">{label}</p>
      <p className={`text-[22px] font-medium mt-0.5 ${highlight ? "text-google-blue" : "text-onsurface"}`}>{value}{unit && <span className="text-[12px] text-onsurface-muted ml-1">{unit}</span>}</p>
    </div>
  );
}

function zFor(serviceLevel: number): number {
  const table: [number, number][] = [[0.9, 1.2816], [0.95, 1.6449], [0.98, 2.0537], [0.99, 2.3263]];
  const closest = table.reduce((best, cur) => Math.abs(cur[0] - serviceLevel) < Math.abs(best[0] - serviceLevel) ? cur : best);
  return closest[1];
}

function ErrorBox({ message }: { message: string }) {
  return <div className="px-3 py-2 rounded-material bg-red-50 text-red-700 text-[13px] mb-3">{message}</div>;
}