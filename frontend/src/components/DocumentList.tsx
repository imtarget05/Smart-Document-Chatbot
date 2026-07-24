import React from "react";
import { formatDistanceToNow } from "date-fns";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Document } from "../types";
import { useAuth } from "../context/AuthContext";

const API_BASE_URL =
  (import.meta.env.VITE_API_URL as string) || "http://localhost:8080/api";

interface DocumentListProps {
  documents: Document[];
  selectedDocument: Document | null;
  onSelectDocument: (doc: Document) => void;
  onDocumentDeleted: (id: number) => void;
  chatMode: "single" | "multi";
  onToggleChatMode: (mode: "single" | "multi") => void;
  selectedDocumentIds: number[];
  onToggleDocumentSelect: (id: number) => void;
  onSelectAllDocuments: () => void;
}

function DocumentList({
  documents,
  selectedDocument,
  onSelectDocument,
  onDocumentDeleted,
  chatMode,
  onToggleChatMode,
  selectedDocumentIds,
  onToggleDocumentSelect,
  onSelectAllDocuments,
}: DocumentListProps) {
  const queryClient = useQueryClient();
  const { token } = useAuth();

  const deleteMutation = useMutation({
    mutationFn: async (id: number) => {
      const response = await fetch(`${API_BASE_URL}/documents/${id}`, {
        method: "DELETE",
        headers: {
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      });
      if (!response.ok) {
        throw new Error("Failed to delete document");
      }
      return id;
    },
    onSuccess: (id) => {
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      onDocumentDeleted(id);
    },
    onError: (error) => {
      console.error("Error deleting document:", error);
      alert(
        "Failed to delete document. Please make sure the service is running.",
      );
    },
  });

  const handleDelete = (id: number, e: React.MouseEvent) => {
    e.stopPropagation();
    if (window.confirm("Are you sure you want to delete this document?")) {
      deleteMutation.mutate(id);
    }
  };

  const isAllSelected =
    documents.length > 0 && selectedDocumentIds.length === documents.length;

  return (
    <div className="p-4">
      {/* Chat Mode Switcher */}
      <div className="flex bg-gray-100 p-1 rounded-xl mb-4 border border-gray-200">
        <button
          type="button"
          onClick={() => onToggleChatMode("single")}
          className={`flex-1 text-center py-2 text-xs font-semibold rounded-lg transition-all duration-200 ${
            chatMode === "single"
              ? "bg-white text-indigo-600 shadow-sm"
              : "text-gray-500 hover:text-gray-800"
          }`}
        >
          Single File
        </button>
        <button
          type="button"
          onClick={() => onToggleChatMode("multi")}
          className={`flex-1 text-center py-2 text-xs font-semibold rounded-lg transition-all duration-200 ${
            chatMode === "multi"
              ? "bg-white text-indigo-600 shadow-sm"
              : "text-gray-500 hover:text-gray-800"
          }`}
        >
          Multi-File Chat
        </button>
      </div>

      <div className="flex items-center justify-between mb-3">
        <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wider">
          Documents
        </h3>
        {chatMode === "multi" && documents.length > 0 && (
          <button
            type="button"
            onClick={onSelectAllDocuments}
            className="text-xs font-semibold text-indigo-600 hover:text-indigo-800 transition"
          >
            {isAllSelected ? "Deselect All" : "Select All"}
          </button>
        )}
      </div>

      <div className="space-y-2">
        {documents.length === 0 ? (
          <div className="text-center py-6 bg-gray-50/50 rounded-xl border border-dashed border-gray-250">
            <p className="text-sm text-gray-400">No documents uploaded yet</p>
          </div>
        ) : (
          documents.map((doc) => {
            const isSelectedInMulti = selectedDocumentIds.includes(doc.id);
            const isSelectedInSingle = selectedDocument?.id === doc.id;

            return (
              <div
                key={doc.id}
                onClick={() => {
                  if (chatMode === "multi") {
                    onToggleDocumentSelect(doc.id);
                  } else {
                    onSelectDocument(doc);
                  }
                }}
                className={`flex items-stretch rounded-xl overflow-hidden cursor-pointer border transition-all duration-200 ${
                  chatMode === "multi"
                    ? isSelectedInMulti
                      ? "bg-indigo-50/60 border-indigo-200 shadow-sm shadow-indigo-100/50"
                      : "bg-white hover:bg-gray-50/80 border-gray-150"
                    : isSelectedInSingle
                      ? "bg-indigo-50/60 border-indigo-200 shadow-sm shadow-indigo-100/50"
                      : "bg-white hover:bg-gray-50/80 border-gray-150"
                }`}
              >
                {chatMode === "multi" && (
                  <div className="flex items-center pl-3 flex-shrink-0">
                    <input
                      type="checkbox"
                      checked={isSelectedInMulti}
                      onChange={() => onToggleDocumentSelect(doc.id)}
                      onClick={(e) => e.stopPropagation()}
                      className="w-4 h-4 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500"
                    />
                  </div>
                )}

                <div className="flex-1 p-3 text-left min-w-0">
                  <p className="text-sm font-semibold text-gray-800 truncate">
                    {doc.fileName}
                  </p>
                  <div className="flex items-center gap-1.5 mt-1">
                    <span className="text-[10px] font-medium bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded">
                      {doc.chunkCount} chunks
                    </span>
                    <span className="text-[10px] font-medium bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded">
                      {(doc.fileSize / 1024).toFixed(0)} KB
                    </span>
                    <span className="text-[10px] text-gray-400">
                      {formatDistanceToNow(new Date(doc.createdAt), {
                        addSuffix: true,
                      })}
                    </span>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={(e) => handleDelete(doc.id, e)}
                  disabled={deleteMutation.isPending}
                  className="px-3 text-gray-400 hover:text-red-500 hover:bg-red-50/50 transition-colors flex-shrink-0 flex items-center justify-center border-l border-gray-100"
                  title="Delete"
                  aria-label={`Delete ${doc.fileName}`}
                >
                  {deleteMutation.isPending &&
                  deleteMutation.variables === doc.id ? (
                    <span className="w-4 h-4 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin"></span>
                  ) : (
                    <span className="text-lg">&times;</span>
                  )}
                </button>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}

export default DocumentList;
