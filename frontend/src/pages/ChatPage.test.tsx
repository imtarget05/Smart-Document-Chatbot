import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthProvider } from "../context/AuthContext";
import ChatPage from "./ChatPage";

function sseBody(events: string) {
  const text = new TextEncoder().encode(events);
  let started = false;
  return {
    getReader: () => ({
      read: async () => {
        if (!started) {
          started = true;
          return { done: false, value: text } as const;
        }
        return { done: true, value: undefined } as const;
      },
    }),
  };
}

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

describe("ChatPage", () => {
  afterEach(cleanup);
  beforeEach(() => {
    vi.restoreAllMocks();
    localStorage.clear();
  });

  it("renders the empty-state placeholder and header", async () => {
    const fetchMock = vi.fn(async (url: string) => {
      if (url.startsWith("/api/documents")) {
        return { ok: true, json: async () => [] };
      }
      if (url.startsWith("/api/chat/history/")) {
        return { ok: true, json: async () => [] };
      }
      throw new Error(`unexpected fetch: ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(
      <QueryClientProvider client={new QueryClient()}>
        <AuthProvider>
          <ChatPage />
        </AuthProvider>
      </QueryClientProvider>,
    );

    expect(screen.getByText("Smart Document Chat")).toBeDefined();
    expect(await screen.findByText("Start a conversation")).toBeDefined();
  });

  it("streams an SSE response and renders the final assistant message", async () => {
    const user = userEvent.setup();
    const events = [
      'event: metadata\ndata: {"ragStrategy":"no_evidence","confidenceScore":0.0,"confidence":"low"}',
      "",
      'event: chunk\ndata: I couldn\'t find sufficient evidence in the document set.',
      "",
      'event: complete\ndata: {"id":1,"sessionId":"s","userMessage":"q","aiResponse":"I couldn\'t find sufficient evidence in the document set.","ragStrategy":"no_evidence"}',
      "",
    ].join("\n");

    const fetchMock = vi.fn(async (url: string) => {
      if (url.startsWith("/api/documents")) {
        return { ok: true, json: async () => [] };
      }
      if (url.startsWith("/api/chat/history/")) {
        return { ok: true, json: async () => [] };
      }
      if (url.startsWith("/api/chat/ask-stream")) {
        return { ok: true, body: sseBody(events) };
      }
      throw new Error(`unexpected fetch: ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    renderChatPage();

    await screen.findByText("Start a conversation");
    await user.type(
      screen.getByPlaceholderText("Type a message... (Shift+Enter for new line)"),
      "What is the refund policy?{enter}",
    );

    await waitFor(() =>
      expect(screen.getByText(/I couldn't find sufficient evidence/)).toBeDefined(),
    );

    const askUrl = fetchMock.mock.calls.map((c) => String(c[0])).find((u) => u.includes("/ask-stream"));
    expect(askUrl).toBeDefined();
    expect(JSON.parse(String(fetchMock.mock.calls.find((c) => String(c[0]).includes("/ask-stream"))?.[1]?.body))).toEqual({
      sessionId: expect.any(String),
      message: "What is the refund policy?",
      documentId: null,
    });
  });

  it("renders an inline error when the stream fails", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.fn(async (url: string) => {
      if (url.startsWith("/api/documents")) {
        return { ok: true, json: async () => [] };
      }
      if (url.startsWith("/api/chat/history/")) {
        return { ok: true, json: async () => [] };
      }
      if (url.startsWith("/api/chat/ask-stream")) {
        return { ok: false, status: 503 };
      }
      throw new Error(`unexpected fetch: ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    renderChatPage();

    await screen.findByText("Start a conversation");
    await user.type(
      screen.getByPlaceholderText("Type a message... (Shift+Enter for new line)"),
      "hello{enter}",
    );

    await waitFor(() => expect(screen.getByText(/❌ Error: .*Streaming/)).toBeDefined());
  });
});