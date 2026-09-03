import { useMutation, useQueryClient } from "@tanstack/react-query";
import { API_BASE_URL } from "../context/apiConfig";
import { csrfHeaders } from "../csrf";

interface RenamePayload {
  title?: string;
  documentNumber?: string;
}

export function useRenameDocument() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ id, payload }: { id: number; payload: RenamePayload }) => {
      const res = await fetch(`${API_BASE_URL}/documents/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json", ...(await csrfHeaders()) },
        credentials: "include",
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || "Đổi tên thất bại");
      }
      return res.json();
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["documents"] });
    },
  });
}

export function useDeleteDocument() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: number) => {
      const res = await fetch(`${API_BASE_URL}/documents/${id}`, {
        method: "DELETE",
        headers: { ...(await csrfHeaders()) },
        credentials: "include",
      });
      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || "Xóa thất bại");
      }
      return res.json();
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["documents"] });
    },
  });
}
