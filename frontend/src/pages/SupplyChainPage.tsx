import { useState } from "react";
import ForecastTab from "../components/SupplyChain/ForecastTab";
import SupplierRiskTab from "../components/SupplyChain/SupplierRiskTab";
import RouteTab from "../components/SupplyChain/RouteTab";
import AnomalyTab from "../components/SupplyChain/AnomalyTab";
import InventoryTab from "../components/SupplyChain/InventoryTab";

const TABS = [
  { id: "forecast", label: "Dự báo nhu cầu", icon: "📈" },
  { id: "supplier", label: "Rủi ro nhà cung cấp", icon: "🛡️" },
  { id: "route", label: "Tối ưu tuyến", icon: "🚚" },
  { id: "anomaly", label: "Bất thường", icon: "🚨" },
  { id: "inventory", label: "Tồn kho", icon: "📦" },
];

export default function SupplyChainPage() {
  const [activeTab, setActiveTab] = useState("forecast");

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-surface-dim min-w-0">
      <div className="px-6 py-4 border-b border-outline bg-surface shrink-0">
        <h1 className="text-[20px] text-onsurface font-normal">Supply Chain Intelligence</h1>
        <p className="text-[13px] text-onsurface-muted mt-0.5">
          Forecast, Supplier Risk, Route Optimization, Anomaly Detection & Inventory Optimization
        </p>
      </div>

      <div className="flex items-center gap-1 px-4 pt-3 pb-0 bg-surface border-b border-outline shrink-0 overflow-x-auto">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-2 px-4 py-2.5 text-[13px] rounded-t-material-full transition shrink-0 ${
              activeTab === tab.id
                ? "text-google-blue bg-google-blue/10 font-medium border-b-2 border-google-blue"
                : "text-onsurface-muted hover:bg-surface-container"
            }`}
          >
            <span>{tab.icon}</span>
            {tab.label}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto p-6">
        {activeTab === "forecast" && <ForecastTab />}
        {activeTab === "supplier" && <SupplierRiskTab />}
        {activeTab === "route" && <RouteTab />}
        {activeTab === "anomaly" && <AnomalyTab />}
        {activeTab === "inventory" && <InventoryTab />}
        <p className="text-[11px] text-onsurface-muted text-center mt-4">
          Dữ liệu thực được tính từ Supply Chain module (FastAPI). Nếu service chưa chạy, backend sẽ trả thông báo lỗi.
        </p>
      </div>
    </div>
  );
}
