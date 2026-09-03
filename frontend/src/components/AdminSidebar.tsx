interface AdminSidebarProps {
  activeTab: string;
  onTabChange: (tab: string) => void;
}

const TABS = [
  { id: "overview", label: "Tổng quan", icon: "📊" },
  { id: "audit", label: "Audit Logs", icon: "📋" },
];

export default function AdminSidebar({ activeTab, onTabChange }: AdminSidebarProps) {
  return (
    <aside className="w-56 h-full bg-surface border-r border-outline flex flex-col shrink-0">
      <div className="p-4 border-b border-outline">
        <h2 className="text-[14px] font-semibold text-onsurface">Admin Dashboard</h2>
        <p className="text-[11px] text-onsurface-muted mt-0.5">Quản trị hệ thống</p>
      </div>
      <nav className="flex-1 p-2 space-y-0.5">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => onTabChange(tab.id)}
            className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-material text-[13px] text-left transition ${
              activeTab === tab.id
                ? "bg-google-blue/10 text-google-blue font-medium"
                : "text-onsurface-variant hover:bg-surface-container"
            }`}
          >
            <span>{tab.icon}</span>
            {tab.label}
          </button>
        ))}
      </nav>
    </aside>
  );
}
