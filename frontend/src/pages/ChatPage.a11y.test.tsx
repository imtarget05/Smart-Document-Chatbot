import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthProvider } from "../context/AuthContext";
import ChatPage from "./ChatPage";

function renderChatPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <ChatPage />
      </AuthProvider>
    </QueryClientProvider>,
  );
}

const mockFetch = () =>
  vi.fn(async (url: string) => {
    if (url.startsWith("/api/documents")) return { ok: true, json: async () => [] };
    if (url.startsWith("/api/chat/history/")) return { ok: true, json: async () => [] };
    throw new Error(`unexpected fetch: ${url}`);
  });

describe("ChatPage accessibility", () => {
  afterEach(cleanup);
  beforeEach(() => {
    vi.restoreAllMocks();
    localStorage.clear();
  });

  it("renders welcome screen with app title", async () => {
    vi.stubGlobal("fetch", mockFetch());
    renderChatPage();
    await screen.findByText(/Chào mừng đến với Smart Document/);
    expect(screen.getAllByText(/Smart Document/).length).toBeGreaterThan(0);
  });

  it("has app bar with user menu button", async () => {
    vi.stubGlobal("fetch", mockFetch());
    renderChatPage();
    await screen.findByText(/Chào mừng/);
    expect(screen.getByLabelText("Menu người dùng")).toBeDefined();
  });

  it("has sidebar with new chat button", async () => {
    vi.stubGlobal("fetch", mockFetch());
    renderChatPage();
    await screen.findByText(/Chào mừng/);
    expect(screen.getByText("Cuộc trò chuyện mới")).toBeDefined();
  });

  it("has sidebar with upload button", async () => {
    vi.stubGlobal("fetch", mockFetch());
    renderChatPage();
    await screen.findByText(/Chào mừng/);
    expect(screen.getByText("Tải lên tài liệu")).toBeDefined();
  });

  it("renders welcome screen with suggested prompts", async () => {
    vi.stubGlobal("fetch", mockFetch());
    renderChatPage();
    await screen.findByText(/Chào mừng/);
    expect(screen.getByText("Tóm tắt tài liệu này")).toBeDefined();
  });
});
