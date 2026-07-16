import { useQuery } from '@tanstack/react-query';

interface AdminUser {
  id: number;
  username: string;
  role: string;
  enabled: boolean;
  createdAt: string;
}

interface Props {
  token: string;
}

const API_BASE_URL = (import.meta.env.VITE_API_URL as string) || 'http://localhost:8080/api';

export default function AdminUsersPage({ token }: Props) {
  const { data = [], isLoading } = useQuery<AdminUser[]>({
    queryKey: ['adminUsers', token],
    queryFn: async () => {
      const res = await fetch(`${API_BASE_URL}/admin/users`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error('Failed to load admin users');
      return res.json();
    },
    enabled: !!token,
  });

  return (
    <div className="p-6 space-y-4">
      <div>
        <h2 className="text-xl font-semibold text-gray-800">Admin Users</h2>
        <p className="text-sm text-gray-500">Manage platform users and their role assignments.</p>
      </div>

      {isLoading ? (
        <div className="rounded-xl border border-dashed border-gray-300 p-6 text-sm text-gray-500">Loading users…</div>
      ) : data.length === 0 ? (
        <div className="rounded-xl border border-dashed border-gray-300 p-6 text-sm text-gray-500">No users found.</div>
      ) : (
        <div className="space-y-3">
          {data.map((user) => (
            <div key={user.id} className="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm">
              <div className="flex items-center justify-between gap-2">
                <div>
                  <h3 className="font-semibold text-gray-800">{user.username}</h3>
                  <p className="text-xs text-gray-500">Created {new Date(user.createdAt).toLocaleDateString()}</p>
                </div>
                <div className="flex items-center gap-2">
                  <span className="rounded-full bg-indigo-50 px-2 py-1 text-[10px] font-semibold uppercase tracking-wide text-indigo-600">
                    {user.role}
                  </span>
                  <span className={`rounded-full px-2 py-1 text-[10px] font-semibold uppercase tracking-wide ${user.enabled ? 'bg-emerald-50 text-emerald-600' : 'bg-rose-50 text-rose-600'}`}>
                    {user.enabled ? 'Enabled' : 'Disabled'}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
