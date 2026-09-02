import { describe, it, expect, afterEach, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

const mockAuth = {
  token: null as string | null,
  username: null as string | null,
  role: null as string | null,
  login: vi.fn(),
  logout: vi.fn(),
  isAuthenticated: false,
  isAdmin: false,
  isEngineer: false,
  isViewer: false,
};

vi.mock("./context/AuthContext", () => ({
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  useAuth: () => mockAuth,
  API_BASE_URL: "/api",
}));

import App from "./App";

afterEach(() => {
  mockAuth.isAuthenticated = false;
  mockAuth.token = null;
});

function renderApp() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>,
  );
}

describe("App routing", () => {
  it("shows the login page when the user is not authenticated", async () => {
    mockAuth.isAuthenticated = false;
    renderApp();
    await waitFor(() =>
      expect(screen.getAllByText("Chào mừng trở lại").length).toBeGreaterThan(0),
    );
    expect(screen.getAllByText(/Smart Document Chatbot/).length).toBeGreaterThan(0);
  });

  it("mounts the chat view (wrapped in ErrorBoundary) when authenticated", async () => {
    mockAuth.isAuthenticated = true;
    mockAuth.token = "fake-jwt";
    renderApp();
    await waitFor(() =>
      expect(screen.getAllByText("Smart Document").length).toBeGreaterThan(0),
    );
    expect(document.body).toBeTruthy();
  });
});
