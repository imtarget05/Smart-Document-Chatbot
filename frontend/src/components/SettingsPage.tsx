import { useState } from "react";

export default function SettingsPage() {
  const [notifications, setNotifications] = useState(true);
  const [autoSync, setAutoSync] = useState(true);

  return (
    <div className="p-6 space-y-4">
      <div>
        <h2 className="text-xl font-semibold text-gray-800">Settings</h2>
        <p className="text-sm text-gray-500">
          Configure platform preferences and operational defaults.
        </p>
      </div>

      <div className="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm space-y-4">
        <label className="flex items-center justify-between gap-3">
          <div>
            <div className="font-medium text-gray-800">Email notifications</div>
            <div className="text-sm text-gray-500">
              Receive updates about workflow completions and failures.
            </div>
          </div>
          <input
            type="checkbox"
            checked={notifications}
            onChange={() => setNotifications(!notifications)}
            className="h-4 w-4 accent-indigo-600"
          />
        </label>
        <label className="flex items-center justify-between gap-3">
          <div>
            <div className="font-medium text-gray-800">
              Auto sync data sources
            </div>
            <div className="text-sm text-gray-500">
              Enable scheduled synchronization for connected sources.
            </div>
          </div>
          <input
            type="checkbox"
            checked={autoSync}
            onChange={() => setAutoSync(!autoSync)}
            className="h-4 w-4 accent-indigo-600"
          />
        </label>
      </div>
    </div>
  );
}
