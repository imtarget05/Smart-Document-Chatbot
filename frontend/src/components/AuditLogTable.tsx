import { useState } from "react";
import { useAuditLogs } from "../hooks/useAuditLogs";
import type { AuditLog } from "../hooks/useAuditLogs";

const PAGE_SIZE = 25;

export default function AuditLogTable() {
  const [page, setPage] = useState(0);
  const [usernameFilter, setUsernameFilter] = useState("");
  const [actionFilter, setActionFilter] = useState("");

  const { data, isLoading, isFetching } = useAuditLogs({
    page,
    size: PAGE_SIZE,
    username: usernameFilter || undefined,
    action: actionFilter || undefined,
  });

  const totalPages = data?.totalPages ?? 0;

  return (
    <div className="flex flex-col h-full">
      <div className="flex flex-wrap gap-3 px-6 py-3 border-b border-outline bg-surface shrink-0">
        <input
          value={usernameFilter}
          onChange={(e) => { setUsernameFilter(e.target.value); setPage(0); }}
          placeholder="Lọc theo username..."
          className="px-3 py-2 border border-outline rounded-material text-[13px] focus:outline-none focus:border-google-blue"
        />
        <select
          value={actionFilter}
          onChange={(e) => { setActionFilter(e.target.value); setPage(0); }}
          className="px-3 py-2 border border-outline rounded-material text-[13px] focus:outline-none focus:border-google-blue"
        >
          <option value="">Tất cả hành động</option>
          <option value="auth.login">auth.login</option>
          <option value="auth.login.failed">auth.login.failed</option>
          <option value="auth.login.sso">auth.login.sso</option>
          <option value="doc.upload">doc.upload</option>
          <option value="chat.ask">chat.ask</option>
        </select>
        {(usernameFilter || actionFilter) && (
          <button onClick={() => { setUsernameFilter(""); setActionFilter(""); setPage(0); }} className="text-[13px] text-google-blue hover:underline">Xóa bộ lọc</button>
        )}
        {isFetching && <span className="text-[12px] text-onsurface-muted ml-auto">Đang tải...</span>}
      </div>

      <div className="flex-1 overflow-auto">
        {isLoading ? (
          <div className="flex items-center justify-center h-full"><span className="w-8 h-8 border-2 border-google-blue border-t-transparent rounded-full animate-spin" /></div>
        ) : !data || data.logs.length === 0 ? (
          <div className="flex items-center justify-center h-full text-onsurface-muted text-[14px]">Không có dữ liệu.</div>
        ) : (
          <table className="w-full text-[13px]">
            <thead className="bg-surface-container sticky top-0">
              <tr className="text-left text-onsurface-muted">
                <th className="px-4 py-2.5 font-medium">Thời gian</th>
                <th className="px-4 py-2.5 font-medium">User</th>
                <th className="px-4 py-2.5 font-medium">Hành động</th>
                <th className="px-4 py-2.5 font-medium">Resource</th>
                <th className="px-4 py-2.5 font-medium">IP</th>
              </tr>
            </thead>
            <tbody>
              {data.logs.map((log) => (
                <LogRow key={log.id} log={log} />
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="flex items-center justify-between px-6 py-3 border-t border-outline bg-surface shrink-0">
        <p className="text-[12px] text-onsurface-muted">{(data?.totalElements ?? 0).toLocaleString("vi-VN")} bản ghi</p>
        <div className="flex items-center gap-2">
          <button disabled={page === 0} onClick={() => setPage((p) => Math.max(0, p - 1))} className="px-3 py-1.5 text-[12px] border border-outline rounded-material disabled:opacity-40 hover:bg-surface-container">← Trước</button>
          <span className="text-[12px] text-onsurface min-w-[60px] text-center">{page + 1} / {Math.max(totalPages, 1)}</span>
          <button disabled={page >= totalPages - 1} onClick={() => setPage((p) => p + 1)} className="px-3 py-1.5 text-[12px] border border-outline rounded-material disabled:opacity-40 hover:bg-surface-container">Sau →</button>
        </div>
      </div>
    </div>
  );
}

function LogRow({ log }: { log: AuditLog }) {
  const color = getActionColor(log.action);
  return (
    <tr className="border-b border-outline/50 hover:bg-surface-container/50 transition">
      <td className="px-4 py-2 text-onsurface-muted whitespace-nowrap">{formatDate(log.createdAt)}</td>
      <td className="px-4 py-2 text-onsurface font-medium">{log.username}</td>
      <td className="px-4 py-2"><span className={`inline-block px-2 py-0.5 rounded-material-full text-[11px] font-medium ${color}`}>{log.action}</span></td>
      <td className="px-4 py-2 text-onsurface-muted">{log.resourceType}:{log.resourceId}</td>
      <td className="px-4 py-2 text-onsurface-muted font-mono text-[11px]">{log.ipAddress}</td>
    </tr>
  );
}

function getActionColor(action: string): string {
  if (action.includes("failed")) return "bg-red-50 text-red-700";
  if (action.startsWith("auth.login")) return "bg-google-green/10 text-google-green";
  if (action.startsWith("doc.") || action.startsWith("document.")) return "bg-google-blue/10 text-google-blue";
  if (action.startsWith("chat.")) return "bg-[#7b1fa2]/10 text-[#7b1fa2]";
  return "bg-surface-container text-onsurface-muted";
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString("vi-VN", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit", second: "2-digit" });
}