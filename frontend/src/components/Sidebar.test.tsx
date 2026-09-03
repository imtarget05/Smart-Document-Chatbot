import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { Document } from "../types";
import Sidebar from "./Sidebar";

const createWrapper = () => {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

afterEach(cleanup);

const mockDocuments: Document[] = [
  {
    id: 1,
    fileName: "doc1.pdf",
    title: "Document One",
    documentNumber: "001",
    fileType: "PDF",
    chunkCount: 10,
    createdAt: "2024-01-01T00:00:00Z",
    sourceType: "USER",
  },
  {
    id: 2,
    fileName: "doc2.docx",
    title: "Document Two",
    documentNumber: "002",
    fileType: "DOCX",
    chunkCount: 5,
    createdAt: "2024-01-02T00:00:00Z",
    sourceType: "USER",
  },
];

function renderSidebar(props: Partial<{
  documents: Document[];
  selectedDoc: Document | null;
  onSelectDoc: (doc: Document | null) => void;
  onNewChat: () => void;
  onUploadClick: () => void;
  isOpen: boolean;
  onClose: () => void;
  activeSessionId: string;
  onSelectSession: (sessionId: string) => void;
}> = {}) {
  return render(
    <Sidebar
      documents={props.documents ?? []}
      selectedDoc={props.selectedDoc ?? null}
      onSelectDoc={props.onSelectDoc ?? vi.fn()}
      onNewChat={props.onNewChat ?? vi.fn()}
      onUploadClick={props.onUploadClick ?? vi.fn()}
      isOpen={props.isOpen ?? false}
      onClose={props.onClose ?? vi.fn()}
      activeSessionId={props.activeSessionId ?? "test-session"}
      onSelectSession={props.onSelectSession ?? vi.fn()}
    />,
    { wrapper: createWrapper() },
  );
}

describe("Sidebar", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders mobile overlay when isOpen is true", () => {
    renderSidebar({ isOpen: true });
    expect(screen.getByTestId("mobile-overlay")).toBeInTheDocument();
  });

  it("does not render mobile overlay when isOpen is false", () => {
    renderSidebar({ isOpen: false });
    expect(screen.queryByTestId("mobile-overlay")).not.toBeInTheDocument();
  });

  it("calls onClose when mobile overlay is clicked", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    renderSidebar({ isOpen: true, onClose });

    await user.click(screen.getByTestId("mobile-overlay"));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("renders new chat button and calls onNewChat + onClose when clicked", async () => {
    const user = userEvent.setup();
    const onNewChat = vi.fn();
    const onClose = vi.fn();
    renderSidebar({ onNewChat, onClose });

    await user.click(screen.getByRole("button", { name: "Cuộc trò chuyện mới" }));
    expect(onNewChat).toHaveBeenCalledTimes(1);
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("renders upload button and calls onUploadClick when clicked", async () => {
    const user = userEvent.setup();
    const onUploadClick = vi.fn();
    renderSidebar({ onUploadClick });

    await user.click(screen.getByRole("button", { name: "Tải lên tài liệu" }));
    expect(onUploadClick).toHaveBeenCalledTimes(1);
  });

  it("shows empty state message when no documents", () => {
    renderSidebar({ documents: [] });
    expect(screen.getByText("Chưa có tài liệu. Tải lên để bắt đầu.")).toBeInTheDocument();
  });

  it("renders document list when documents exist", () => {
    renderSidebar({ documents: mockDocuments });
    // Component shows doc.title || doc.fileName, so titles are displayed
    expect(screen.getByText("Document One")).toBeInTheDocument();
    expect(screen.getByText("Document Two")).toBeInTheDocument();
    expect(screen.getByText(/10 chunks/)).toBeInTheDocument();
    expect(screen.getByText(/5 chunks/)).toBeInTheDocument();
  });

  it("shows document title when available", () => {
    renderSidebar({ documents: mockDocuments });
    expect(screen.getByText("Document One")).toBeInTheDocument();
    expect(screen.getByText("Document Two")).toBeInTheDocument();
  });

  it("shows document number when available", () => {
    renderSidebar({ documents: mockDocuments });
    expect(screen.getByText(/Số: 001/)).toBeInTheDocument();
    expect(screen.getByText(/Số: 002/)).toBeInTheDocument();
  });

  it("highlights selected document", () => {
    const onSelectDoc = vi.fn();
    renderSidebar({ documents: mockDocuments, selectedDoc: mockDocuments[0], onSelectDoc });

    const selectedButton = screen.getByText("Document One").closest("button");
    expect(selectedButton).toHaveClass("bg-google-blue/10");
    expect(selectedButton).toHaveClass("text-google-blue");

    const unselectedButton = screen.getByText("Document Two").closest("button");
    expect(unselectedButton).not.toHaveClass("bg-google-blue/10");
    expect(unselectedButton).not.toHaveClass("text-google-blue");
  });

  it("calls onSelectDoc and onClose when document is clicked", async () => {
    const user = userEvent.setup();
    const onSelectDoc = vi.fn();
    const onClose = vi.fn();
    renderSidebar({ documents: mockDocuments, onSelectDoc, onClose });

    await user.click(screen.getByText("Document One"));
    expect(onSelectDoc).toHaveBeenCalledWith(mockDocuments[0]);
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("does not highlight any document when selectedDoc is null", () => {
    renderSidebar({ documents: mockDocuments, selectedDoc: null });
    const buttons = screen.getAllByRole("button", { name: /Document/ });
    buttons.forEach((btn) => {
      expect(btn).not.toHaveClass("bg-google-blue/10");
      expect(btn).not.toHaveClass("text-google-blue");
    });
  });

  it("renders footer text", () => {
    renderSidebar();
    expect(screen.getByText("Smart Doc \u2022 Enterprise CRAG")).toBeInTheDocument();
  });

  it("applies correct transform classes based on isOpen", () => {
    const { container: closedContainer } = renderSidebar({ isOpen: false });
    const closedSidebar = closedContainer.querySelector("aside");
    expect(closedSidebar).toHaveClass("-translate-x-full");
    expect(closedSidebar).toHaveClass("lg:translate-x-0");

    const { container: openContainer } = renderSidebar({ isOpen: true });
    const openSidebar = openContainer.querySelector("aside");
    expect(openSidebar).toHaveClass("translate-x-0");
  });
});