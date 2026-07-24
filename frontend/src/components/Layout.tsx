import { useState } from "react";
import { useNavigate, useLocation, Outlet } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Layout() {
  const { username, role, logout, isAdmin, isEngineer } = useAuth();
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const navigate = useNavigate();
  const location = useLocation();

  const navItems = [
    {
      path: "/classic",
      label: "💬 Classic Chat",
      description: "Document Q&A",
      roles: ["ALL"],
    },
    {
      path: "/dashboard",
      label: "📊 Dashboard",
      description: "Overview",
      roles: ["ALL"],
    },
    {
      path: "/agent",
      label: "🤖 Agent Chat",
      description: "Multi-agent",
      roles: ["ALL"],
    },
    {
      path: "/knowledge",
      label: "📚 Knowledge Base",
      description: "Docs & playbooks",
      roles: ["ALL"],
    },
    {
      path: "/datasources",
      label: "🔌 Data Sources",
      description: "Connectors",
      roles: ["ALL"],
    },
    {
      path: "/eightd",
      label: "🧰 8D Cases",
      description: "Incidents",
      roles: ["ENGINEER", "ADMIN"],
    },
    {
      path: "/evaluation",
      label: "📈 Evaluation Lab",
      description: "Quality",
      roles: ["ENGINEER", "ADMIN"],
    },
    {
      path: "/audit",
      label: "🧾 Audit Logs",
      description: "Security",
      roles: ["ADMIN"],
    },
    {
      path: "/settings",
      label: "⚙️ Settings",
      description: "Preferences",
      roles: ["ALL"],
    },
    {
      path: "/admin",
      label: "🛡️ Admin",
      description: "Users",
      roles: ["ADMIN"],
    },
  ];

  const filteredNavItems = navItems.filter((item) => {
    if (item.roles.includes("ALL")) return true;
    if (item.roles.includes("ADMIN") && isAdmin) return true;
    if (item.roles.includes("ENGINEER") && (isEngineer || isAdmin)) return true;
    return false;
  });

  const isActive = (path: string) => {
    if (path === "/classic")
      return location.pathname === "/" || location.pathname === "/classic";
    return location.pathname.startsWith(path);
  };

  const displayRole = role?.replace("ROLE_", "") || "VIEWER";

  return (
    <div className="flex h-screen bg-gray-100 font-sans">
      {/* Sidebar */}
      <div
        className={`${sidebarOpen ? "w-72" : "w-0"} transition-all duration-300 overflow-hidden bg-white border-r border-gray-200 flex flex-col`}
      >
        <div className="p-4 border-b border-gray-200">
          <h1
            className="text-lg font-bold text-gray-800 flex items-center gap-2 cursor-pointer"
            onClick={() => navigate("/")}
          >
            <span>📚</span> Smart Doc Chat
          </h1>
          <div className="flex items-center justify-between mt-1">
            <p className="text-xs text-gray-400">
              User:{" "}
              <span className="font-semibold text-gray-600">{username}</span>
            </p>
            <p className="text-[10px] font-bold text-indigo-600 bg-indigo-50 border border-indigo-100 px-1.5 py-0.5 rounded">
              {displayRole}
            </p>
          </div>
        </div>

        <div className="p-3 space-y-3 flex-1 overflow-y-auto">
          <button
            onClick={() => {
              navigate("/classic");
            }}
            className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold rounded-xl shadow-md transition flex items-center justify-center gap-2"
          >
            <span>+</span> New Conversation
          </button>

          <div className="rounded-xl border border-gray-200 bg-gray-50 p-2.5">
            <div className="mb-2 px-1 text-[10px] font-semibold uppercase tracking-[0.2em] text-gray-400">
              Workspace
            </div>
            <div className="space-y-1">
              {filteredNavItems.map((item) => (
                <button
                  key={item.path}
                  onClick={() => navigate(item.path)}
                  className={`w-full rounded-lg border px-2.5 py-2 text-left transition ${
                    isActive(item.path)
                      ? "border-indigo-200 bg-indigo-600 text-white shadow-sm"
                      : "border-transparent bg-white text-gray-600 hover:border-indigo-100 hover:bg-indigo-50 hover:text-indigo-600"
                  }`}
                >
                  <div className="text-[11px] font-semibold">{item.label}</div>
                  <div
                    className={`mt-0.5 text-[10px] ${isActive(item.path) ? "text-indigo-100" : "text-gray-400"}`}
                  >
                    {item.description}
                  </div>
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Logout Section */}
        <div className="p-4 border-t border-gray-200 bg-gray-50/50 flex items-center justify-between">
          <p className="text-[10px] text-gray-400 font-bold uppercase tracking-wider">
            Session active
          </p>
          <button
            onClick={logout}
            className="text-xs font-bold text-rose-500 hover:text-rose-700 transition"
          >
            Logout 🚪
          </button>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top bar */}
        <div className="bg-white border-b border-gray-200 px-6 py-3 flex items-center shadow-sm flex-shrink-0">
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="p-2 hover:bg-gray-100 rounded-lg transition text-gray-500"
            aria-label={sidebarOpen ? "Hide sidebar" : "Show sidebar"}
          >
            {sidebarOpen ? "←" : "→"}
          </button>
          <span className="ml-4 text-sm font-semibold text-gray-600">
            {navItems.find((item) => isActive(item.path))?.description ||
              "Workspace"}
          </span>
        </div>

        {/* Page content */}
        <div className="flex-1 overflow-y-auto">
          <Outlet />
        </div>
      </div>
    </div>
  );
}
