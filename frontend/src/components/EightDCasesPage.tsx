import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";

interface EightDCase {
  id: number;
  title: string;
  severity: string;
  status: string;
  owner: string;
  summary: string;
  d1Team?: string;
  d2Describe?: string;
  d3Containment?: string;
  d4RootCause?: string;
  d5Corrective?: string;
  d6Verification?: string;
  d7Preventive?: string;
  d8Recognition?: string;
  timeline?: string;
  aiSuggestions?: string;
  documentId?: number;
  createdAt: string;
  updatedAt?: string;
}

interface Props {
  token: string;
}

const API_BASE_URL =
  (import.meta.env.VITE_API_URL as string) || "http://localhost:8080/api";

const EIGHT_D_STEPS = [
  { key: "d1Team", label: "D1", title: "Team Establishment", icon: "👥" },
  { key: "d2Describe", label: "D2", title: "Problem Description", icon: "📝" },
  {
    key: "d3Containment",
    label: "D3",
    title: "Containment Actions",
    icon: "🛑",
  },
  { key: "d4RootCause", label: "D4", title: "Root Cause Analysis", icon: "🔍" },
  { key: "d5Corrective", label: "D5", title: "Corrective Actions", icon: "🔧" },
  { key: "d6Verification", label: "D6", title: "Verification", icon: "✅" },
  {
    key: "d7Preventive",
    label: "D7",
    title: "Preventive Measures",
    icon: "🛡️",
  },
  {
    key: "d8Recognition",
    label: "D8",
    title: "Recognition & Closure",
    icon: "🏆",
  },
];

const severityColors: Record<string, string> = {
  CRITICAL: "bg-rose-50 text-rose-600 border-rose-200",
  HIGH: "bg-orange-50 text-orange-600 border-orange-200",
  MEDIUM: "bg-amber-50 text-amber-600 border-amber-200",
  LOW: "bg-emerald-50 text-emerald-600 border-emerald-200",
};

const statusColors: Record<string, string> = {
  OPEN: "bg-blue-50 text-blue-600 border-blue-200",
  IN_PROGRESS: "bg-indigo-50 text-indigo-600 border-indigo-200",
  CLOSED: "bg-gray-50 text-gray-600 border-gray-200",
};

export default function EightDCasesPage({ token }: Props) {
  const queryClient = useQueryClient();
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [newCase, setNewCase] = useState({
    title: "",
    severity: "MEDIUM",
    owner: "",
    summary: "",
  });
  const [showCreate, setShowCreate] = useState(false);
  const [editingStep, setEditingStep] = useState<{
    caseId: number;
    step: string;
  } | null>(null);
  const [stepContent, setStepContent] = useState("");

  const { data = [], isLoading } = useQuery<EightDCase[]>({
    queryKey: ["eightdCases", token],
    queryFn: async () => {
      const res = await fetch(`${API_BASE_URL}/8d-cases`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("Failed to load 8D cases");
      return res.json();
    },
    enabled: !!token,
  });

  const createMutation = useMutation({
    mutationFn: async (payload: any) => {
      const res = await fetch(`${API_BASE_URL}/8d-cases`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error("Failed to create case");
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["eightdCases"] });
      setShowCreate(false);
      setNewCase({ title: "", severity: "MEDIUM", owner: "", summary: "" });
    },
  });

  const updateStepMutation = useMutation({
    mutationFn: async ({
      caseId,
      step,
      content,
    }: {
      caseId: number;
      step: string;
      content: string;
    }) => {
      const res = await fetch(
        `${API_BASE_URL}/8d-cases/${caseId}/step/${step}`,
        {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ content }),
        },
      );
      if (!res.ok) throw new Error("Failed to update step");
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["eightdCases"] });
      setEditingStep(null);
      setStepContent("");
    },
  });

  const updateStatusMutation = useMutation({
    mutationFn: async ({
      caseId,
      status,
    }: {
      caseId: number;
      status: string;
    }) => {
      await fetch(`${API_BASE_URL}/8d-cases/${caseId}/status`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ status }),
      });
    },
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["eightdCases"] }),
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: number) => {
      await fetch(`${API_BASE_URL}/8d-cases/${id}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });
    },
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["eightdCases"] }),
  });

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-gray-800">
            8D Problem Solving
          </h2>
          <p className="text-sm text-gray-500">
            Track problem reports and corrective actions using the 8D
            methodology.
          </p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold rounded-xl shadow-md transition"
        >
          + New 8D Case
        </button>
      </div>

      {/* Create Form */}
      {showCreate && (
        <div className="rounded-2xl border border-indigo-200 bg-indigo-50/30 p-4 space-y-3">
          <h3 className="font-semibold text-indigo-800 text-sm">
            Create New 8D Case
          </h3>
          <input
            type="text"
            placeholder="Case title"
            value={newCase.title}
            onChange={(e) =>
              setNewCase((p) => ({ ...p, title: e.target.value }))
            }
            className="w-full px-3 py-2 border border-gray-200 rounded-xl text-sm"
          />
          <div className="flex gap-3">
            <select
              value={newCase.severity}
              onChange={(e) =>
                setNewCase((p) => ({ ...p, severity: e.target.value }))
              }
              className="flex-1 px-3 py-2 border border-gray-200 rounded-xl text-sm bg-white"
            >
              <option value="LOW">Low</option>
              <option value="MEDIUM">Medium</option>
              <option value="HIGH">High</option>
              <option value="CRITICAL">Critical</option>
            </select>
            <input
              type="text"
              placeholder="Owner"
              value={newCase.owner}
              onChange={(e) =>
                setNewCase((p) => ({ ...p, owner: e.target.value }))
              }
              className="flex-1 px-3 py-2 border border-gray-200 rounded-xl text-sm"
            />
          </div>
          <textarea
            placeholder="Summary"
            value={newCase.summary}
            onChange={(e) =>
              setNewCase((p) => ({ ...p, summary: e.target.value }))
            }
            className="w-full px-3 py-2 border border-gray-200 rounded-xl text-sm"
            rows={2}
          />
          <div className="flex gap-2">
            <button
              onClick={() => createMutation.mutate(newCase)}
              disabled={!newCase.title || createMutation.isPending}
              className="px-4 py-2 bg-indigo-600 text-white text-xs font-bold rounded-xl disabled:opacity-50"
            >
              {createMutation.isPending ? "Creating..." : "Create"}
            </button>
            <button
              onClick={() => setShowCreate(false)}
              className="px-4 py-2 bg-gray-200 text-gray-600 text-xs font-bold rounded-xl"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Cases List */}
      {isLoading ? (
        <div className="rounded-xl border border-dashed border-gray-300 p-6 text-sm text-gray-500">
          Loading 8D cases…
        </div>
      ) : data.length === 0 ? (
        <div className="rounded-xl border border-dashed border-gray-300 p-8 text-center text-sm text-gray-500">
          <div className="text-3xl mb-3">🧰</div>
          <p className="font-semibold text-gray-600">No 8D cases yet</p>
          <p className="text-xs mt-1">
            Create a case to start the 8D problem-solving workflow.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {data.map((kase) => (
            <div
              key={kase.id}
              className="rounded-2xl border border-gray-200 bg-white shadow-sm overflow-hidden"
            >
              {/* Header */}
              <div
                className="p-4 flex items-center justify-between cursor-pointer"
                onClick={() =>
                  setExpandedId(expandedId === kase.id ? null : kase.id)
                }
              >
                <div className="flex items-center gap-3">
                  <span className="text-lg">
                    {expandedId === kase.id ? "▼" : "▶"}
                  </span>
                  <div>
                    <h3 className="font-semibold text-gray-800 text-sm">
                      {kase.title}
                    </h3>
                    <p className="text-xs text-gray-400">Owner: {kase.owner}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span
                    className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase border ${severityColors[kase.severity] || ""}`}
                  >
                    {kase.severity}
                  </span>
                  <span
                    className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase border ${statusColors[kase.status] || ""}`}
                  >
                    {kase.status}
                  </span>
                </div>
              </div>

              {/* Expanded Detail */}
              {expandedId === kase.id && (
                <div className="border-t border-gray-100 bg-gray-50/50 p-4 space-y-3">
                  {kase.summary && (
                    <div className="rounded-xl bg-white border border-gray-100 p-3">
                      <p className="text-xs font-bold text-gray-400 uppercase mb-1">
                        Summary
                      </p>
                      <p className="text-sm text-gray-600">{kase.summary}</p>
                    </div>
                  )}

                  {/* 8D Steps Grid */}
                  <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-4">
                    {EIGHT_D_STEPS.map((step) => {
                      const content = (kase as any)[step.key];
                      const filled = !!content;
                      const isEditing =
                        editingStep?.caseId === kase.id &&
                        editingStep?.step === step.label;

                      return (
                        <div
                          key={step.key}
                          className={`rounded-xl border p-3 ${filled ? "border-emerald-200 bg-emerald-50/30" : "border-gray-200 bg-white"}`}
                        >
                          <div className="flex items-center justify-between mb-1">
                            <span className="text-[10px] font-bold text-gray-400">
                              {step.icon} {step.label}
                            </span>
                            {filled && (
                              <span className="text-[10px] text-emerald-600">
                                ✓
                              </span>
                            )}
                          </div>
                          <p className="text-[11px] font-semibold text-gray-700 mb-1">
                            {step.title}
                          </p>
                          {filled ? (
                            <p className="text-[11px] text-gray-500 line-clamp-2">
                              {content}
                            </p>
                          ) : (
                            <p className="text-[11px] text-gray-300 italic">
                              Not started
                            </p>
                          )}
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              setEditingStep({
                                caseId: kase.id,
                                step: step.label,
                              });
                              setStepContent(content || "");
                            }}
                            className="mt-2 text-[10px] font-bold text-indigo-500 hover:text-indigo-700"
                          >
                            {filled ? "Edit" : "Add"}
                          </button>

                          {isEditing && (
                            <div
                              className="mt-2 space-y-2"
                              onClick={(e) => e.stopPropagation()}
                            >
                              <textarea
                                value={stepContent}
                                onChange={(e) => setStepContent(e.target.value)}
                                className="w-full px-2 py-1 border border-gray-200 rounded-lg text-[11px]"
                                rows={3}
                                placeholder={`Describe ${step.title}...`}
                              />
                              <div className="flex gap-1">
                                <button
                                  onClick={() =>
                                    updateStepMutation.mutate({
                                      caseId: kase.id,
                                      step: step.label,
                                      content: stepContent,
                                    })
                                  }
                                  disabled={updateStepMutation.isPending}
                                  className="px-2 py-1 bg-indigo-600 text-white text-[10px] font-bold rounded-lg"
                                >
                                  Save
                                </button>
                                <button
                                  onClick={() => {
                                    setEditingStep(null);
                                    setStepContent("");
                                  }}
                                  className="px-2 py-1 bg-gray-200 text-gray-600 text-[10px] font-bold rounded-lg"
                                >
                                  Cancel
                                </button>
                              </div>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>

                  {/* AI Suggestions */}
                  {kase.aiSuggestions && (
                    <div className="rounded-xl bg-indigo-50 border border-indigo-100 p-3">
                      <p className="text-xs font-bold text-indigo-600 mb-1">
                        🤖 AI Suggestions
                      </p>
                      <p className="text-xs text-indigo-700 whitespace-pre-wrap">
                        {kase.aiSuggestions}
                      </p>
                    </div>
                  )}

                  {/* Actions */}
                  <div className="flex gap-2 pt-2 border-t border-gray-200">
                    {kase.status !== "CLOSED" && (
                      <button
                        onClick={() =>
                          updateStatusMutation.mutate({
                            caseId: kase.id,
                            status: "CLOSED",
                          })
                        }
                        className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white text-[10px] font-bold rounded-lg"
                      >
                        Close Case
                      </button>
                    )}
                    {kase.status === "OPEN" && (
                      <button
                        onClick={() =>
                          updateStatusMutation.mutate({
                            caseId: kase.id,
                            status: "IN_PROGRESS",
                          })
                        }
                        className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white text-[10px] font-bold rounded-lg"
                      >
                        Start Progress
                      </button>
                    )}
                    <button
                      onClick={() => {
                        if (window.confirm("Delete this case?"))
                          deleteMutation.mutate(kase.id);
                      }}
                      className="px-3 py-1.5 bg-rose-100 hover:bg-rose-200 text-rose-600 text-[10px] font-bold rounded-lg ml-auto"
                    >
                      Delete
                    </button>
                  </div>

                  {/* Timeline */}
                  <div className="text-[10px] text-gray-400">
                    Created: {new Date(kase.createdAt).toLocaleString()}
                    {kase.updatedAt &&
                      ` • Updated: ${new Date(kase.updatedAt).toLocaleString()}`}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
