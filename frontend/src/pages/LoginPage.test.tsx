import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AuthProvider } from "../context/AuthContext";
import LoginPage from "./LoginPage";

afterEach(cleanup);

describe("LoginPage", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders the login form by default", () => {
    render(
      <AuthProvider>
        <LoginPage />
      </AuthProvider>,
    );
    expect(screen.getAllByText("Sign In").length).toBeGreaterThan(0);
    expect(screen.getByPlaceholderText("Enter username")).toBeDefined();
    expect(screen.getByPlaceholderText("Enter password")).toBeDefined();
  });

  it("shows a validation error when fields are empty", async () => {
    const user = userEvent.setup();
    render(
      <AuthProvider>
        <LoginPage />
      </AuthProvider>,
    );
    await user.click(screen.getAllByRole("button", { name: "Sign In" })[1]);
    expect(await screen.findByText(/Please fill in all fields/)).toBeDefined();
  });

  it("calls POST /api/auth/login with credentials on successful submit", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ token: "jwt-abc", username: "alice", role: "ROLE_ADMIN" }),
    });
    vi.stubGlobal("fetch", fetchMock);

    render(
      <AuthProvider>
        <LoginPage />
      </AuthProvider>,
    );

    await user.type(screen.getByPlaceholderText("Enter username"), "alice");
    await user.type(screen.getByPlaceholderText("Enter password"), "secret");
    await user.click(screen.getAllByRole("button", { name: "Sign In" })[1]);

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/auth/login");
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body)).toEqual({ username: "alice", password: "secret" });
  });

  it("shows the backend error text when credentials are rejected", async () => {
    const user = userEvent.setup();
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        text: async () => "Bad credentials",
      }),
    );

    render(
      <AuthProvider>
        <LoginPage />
      </AuthProvider>,
    );

    await user.type(screen.getByPlaceholderText("Enter username"), "alice");
    await user.type(screen.getByPlaceholderText("Enter password"), "wrong");
    await user.click(screen.getAllByRole("button", { name: "Sign In" })[1]);

    expect(await screen.findByText(/Bad credentials/)).toBeDefined();
  });

  it("switches to register mode and calls POST /api/auth/register", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ token: "jwt-new", username: "bob", role: "ROLE_VIEWER" }),
    });
    vi.stubGlobal("fetch", fetchMock);

    render(
      <AuthProvider>
        <LoginPage />
      </AuthProvider>,
    );

    await user.click(screen.getByText("Create Account"));
    expect(screen.getAllByText("Create Account").length).toBeGreaterThan(0);

    await user.type(screen.getByPlaceholderText("Enter username"), "bob");
    await user.type(screen.getByPlaceholderText("Enter password"), "pw1234");
    const submitButton = screen.getAllByRole("button", { name: "Create Account" })[1];
    await user.click(submitButton);

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    expect(fetchMock.mock.calls[0][0]).toBe("/api/auth/register");
  });
});