import { useState } from "react";
import { useSupplierRisk } from "../../hooks/useSupplyChain";

export default function SupplierRiskTab() {
  const mutation = useSupplierRisk();
  const [leadTime, setLeadTime] = useState("4.5");
  const [defect, setDefect] = useState("0.03");
  const [onTime, setOnTime] = useState("0.92");

  const data = mutation.data;

  function submit(e: React.FormEvent) {
    e.preventDefault();
    mutation.mutate({
      lead_time_std: Number(leadTime) || 0,
      defect_rate: Number(defect) || 0,
      on_time_rate: Number(onTime) || 0,
    });
  }

  const grade = data?.risk_grade;
  const gradeColor = {
    A: "bg-google-green/10 text-google-green",
    B: "bg-[#00796b]/10 text-[#00796b]",
    C: "bg-amber-50 text-amber-700",
    D: "bg-red-50 text-red-700",
  }[grade ?? "A"] ?? "bg-surface-container text-onsurface-muted";

  return (
    <div className="bg-surface border border-outline rounded-material-lg p-5">
      <h3 className="text-[15px] text-onsurface font-medium">🛡️ Đánh giá rủi ro nhà cung cấp</h3>
      <p className="text-[12px] text-onsurface-muted mt-0.5 mb-4">LogisticRegression/MLflow hoặc rule-based fallback</p>

      <form onSubmit={submit} className="mb-5 space-y-3">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <Field label="Độ lệch lead time (σ)" value={leadTime} onChange={setLeadTime} />
          <Field label="Tỷ lệ lỗi (0-1)" value={defect} onChange={setDefect} />
          <Field label="Tỷ lệ đúng hẹn (0-1)" value={onTime} onChange={setOnTime} />
        </div>
        <button type="submit" disabled={mutation.isPending} className="px-4 py-2 rounded-material bg-google-blue text-white text-[13px] font-medium hover:bg-google-blue/90 disabled:opacity-50">
          {mutation.isPending ? "Đang tính..." : "Đánh giá"}
        </button>
      </form>

      {mutation.isError && <ErrorBox message="Không thể kết nối Supply Chain service." />}
      {data?.error && <ErrorBox message={String(data.error)} />}

      {data && !data.error && data.risk_score !== undefined && (
        <div>
          <div className="flex items-center gap-3 mb-4">
            <div className="flex-1">
              <p className="text-[11px] text-onsurface-muted">Risk Score</p>
              <p className="text-[34px] text-onsurface font-medium">{data.risk_score}<span className="text-[16px] text-onsurface-muted">/100</span></p>
            </div>
            <span className={`inline-block px-3 py-1.5 rounded-material-full text-[13px] font-semibold ${gradeColor}`}>
              Hạng {grade}
            </span>
          </div>
          <ResultBar score={data.risk_score} />
          {data.components && (
            <div className="grid grid-cols-3 gap-3 mt-4">
              <MiniMetric label="Lead time var." value={data.components.lead_time_variability} max={40} />
              <MiniMetric label="Defect rate" value={data.components.defect_rate} max={40} />
              <MiniMetric label="On-time thiếu" value={data.components.on_time} max={30} />
            </div>
          )}
          {data.method && <p className="text-[11px] text-onsurface-muted mt-3">Phương pháp: {data.method}</p>}
        </div>
      )}
    </div>
  );
}

function Field({ label, value, onChange }: { label: string; value: string; onChange: (v: string) => void }) {
  return (
    <div>
      <label className="block text-[12px] text-onsurface-muted mb-1">{label}</label>
      <input value={value} type="number" step="0.01" onChange={(e) => onChange(e.target.value)} className="w-full px-3 py-2 border border-outline rounded-material text-[13px] font-mono focus:outline-none focus:border-google-blue" />
    </div>
  );
}

function ResultBar({ score }: { score: number }) {
  const barColor = score < 25 ? "bg-google-green" : score < 50 ? "bg-[#00796b]" : score < 75 ? "bg-amber-500" : "bg-red-500";
  return (
    <div className="h-2 w-full rounded-material-full bg-surface-container overflow-hidden">
      <div className={`h-full ${barColor}`} style={{ width: `${Math.min(score, 100)}%` }} />
    </div>
  );
}

function MiniMetric({ label, value, max }: { label: string; value: number; max: number }) {
  return (
    <div className="bg-surface-container rounded-material p-3">
      <p className="text-[11px] text-onsurface-muted mb-1">{label}</p>
      <p className="text-[16px] text-onsurface font-medium">{value}</p>
      <div className="h-1 w-full bg-outline/40 rounded-material-full mt-1 overflow-hidden">
        <div className="h-full bg-google-blue" style={{ width: `${Math.min((value / max) * 100, 100)}%` }} />
      </div>
    </div>
  );
}

function ErrorBox({ message }: { message: string }) {
  return <div className="px-3 py-2 rounded-material bg-red-50 text-red-700 text-[13px] mb-3">{message}</div>;
}