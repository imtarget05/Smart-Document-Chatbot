import { describe, it, expect, vi, afterEach, beforeEach } from "vitest";
import { render, screen, cleanup, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthProvider } from "../context/AuthContext";
import DocumentViewer from "./DocumentViewer";
import type { SourceCitation } from "../types";

afterEach(cleanup);

const citation: SourceCitation = {
  documentId: 7,
  documentTitle: "Bộ luật Test",
  documentNumber: "01/2026/TEST",
  sourceType: "OFFICIAL",
  content: "Người lao động...",
  article: "35",
  clause: "1",
  point: "a",
  chunkId: 42,
};

function renderViewer(ui: React.ReactNode) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <AuthProvider>{ui}</AuthProvider>
    </QueryClientProvider>,
  );
}

describe("DocumentViewer", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("shows honest loading then error when the document fetch fails", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.resolve({ ok: false, status: 404, json: async () => ({}) })),
    );
    renderViewer(<DocumentViewer citation={citation} token="tok" onClose={() => {}} />);

    // error state surfaces an honest message (owner-isolation 404)
    await waitFor(() =>
      expect(screen.getByTestId("viewer-error")).toHaveTextContent("Không thể mở tài liệu này."),
    );
    // The viewer shell stays mounted with a neutral title fallback
    expect(screen.getByTestId("viewer-title")).toHaveTextContent("Không xác định tên văn bản");
  });

  it("renders structured legal chunks with the cited chunk highlighted", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve({
          ok: true,
          json: async () => ({
            documentId: 7,
            fileName: "bo_luat.pdf",
            title: "Bộ luật Test",
            documentNumber: "01/2026/TEST",
            sourceType: "OFFICIAL",
            chunks: [
              { id: 42, ordinal: 1, article: "35", clause: "1", point: "a", content: "Nội dung A" },
              { id: 43, ordinal: 2, article: "36", content: "Nội dung B" },
            ],
          }),
        }),
      ),
    );
    renderViewer(<DocumentViewer citation={citation} token="tok" onClose={() => {}} />);

    await waitFor(() => expect(screen.getByText("Nội dung A")).toBeInTheDocument());
    expect(screen.getByText("Nội dung B")).toBeInTheDocument();
    expect(screen.getByText("Điều 35 · Khoản 1 · Điểm a")).toBeInTheDocument();
    // The cited chunk is flagged, the other is not
    expect(screen.getByText("Nội dung A").closest("[data-cited]")).not.toBeNull();
    expect(screen.getByText("Nội dung B").closest("[data-cited]")).toBeNull();
  });

  it("invokes onClose when the backdrop or close button is clicked", async () => {
    const onClose = vi.fn();
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve({
          ok: true,
          json: async () => ({ documentId: 7, fileName: "f.pdf", chunks: [] }),
        }),
      ),
    );
    renderViewer(<DocumentViewer citation={citation} token="tok" onClose={onClose} />);
    await waitFor(() => expect(screen.getByTestId("document-viewer")).toBeInTheDocument());

    screen.getByLabelText("Đóng").click();
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("falls back to the file name when no title is present", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve({
          ok: true,
          json: async () => ({ documentId: 7, fileName: "thong_tu.pdf", chunks: [] }),
        }),
      ),
    );
    renderViewer(<DocumentViewer citation={{ documentId: 7 }} token="tok" onClose={() => {}} />);
    await waitFor(() =>
      expect(screen.getByTestId("viewer-title")).toHaveTextContent("thong_tu.pdf"),
    );
  });
});
