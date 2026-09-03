import { useState } from "react";
import { useAuth } from "../context/AuthContext";
import AdminSidebar from "../components/AdminSidebar";
import AuditLogTable from "../components/AuditLogTable";

export default function AdminPage() {
  const { isAdmin } = useAuth();
  const [activeTab, setActiveTab] = useState("overview");

  if (!isAdmin) {
    return (
      <div className="flex-1 flex items-center justify-center bg-surface-dim">
        <div className="text-center">
          <span className="text-4xl">🔒</span>
          <p className="text-[14px] text-onsurface-muted mt-2">Bạn không có quyền truy cập trang quản trị.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-1 overflow-hidden">
      <AdminSidebar activeTab={activeTab} onTabChange={setActiveTab} />
      <main className="flex-1 flex flex-col overflow-hidden bg-surface-dim">
        {activeTab === "overview" && <AdminOverview />}
        {activeTab === "audit" && <AuditLogTable />}
      </main>
    </div>
  );
}

function AdminOverview() {
  return (
    <div className="p-6 overflow-y-auto">
      <h1 className="text-[20px] text-onsurface font-normal mb-6">Tổng quan hệ thống</h1>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <StatCard label="Tài liệu" value="—" icon="📄" />
        <StatCard label="Người dùng" value="—" icon="👤" />
        <StatCard label="Phiên chat" value="—" icon="💬" />
      </div>
      <p className="text-[13px] text-onsurface-muted">
        Chọn "Audit Logs" ở menu bên trái để xem nhật ký hoạt động chi tiết.
      </p>
    </div>
  );
}

function StatCard({ label, value, icon }: { label: string; value: string; icon: string }) {
  return (
    <div className="bg-surface border border-outline rounded-material-lg p-4 shadow-material-1">
      <div className="flex items-center gap-3">
        <span className="text-[24px]">{icon}</span>
        <div>
          <p className="text-[24px] font-normal text-onsurface">{value}</p>
          <p className="text-[12px] text-onsurface-muted">{label}</p>
        </div>
      </div>
    </div>
  );
}
