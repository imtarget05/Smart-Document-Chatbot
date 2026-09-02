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
    expect(screen.getAllByText("Chào mừng trở lại").length).toBeGreaterThan(0);
    expect(screen.getByPlaceholderText("Email hoặc tên đăng nhập")).toBeDefined();
    expect(screen.getByPlaceholderText("Mật khẩu")).toBeDefined();
  });

  it("shows a validation error when fields are empty", async () => {
    const user = userEvent.setup();
    render(
      <AuthProvider>
        <LoginPage />
      </AuthProvider>,
    );
    await user.click(screen.getByRole("button", { name: "Tiếp tục" }));
    expect(await screen.findByText(/Vui lòng điền đầy đủ thông tin/)).toBeDefined();
  });

  it("calls POST /api/auth/login with credentials on successful submit", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.fn((url: RequestInfo) =>
      String(url).includes("/csrf")
        ? Promise.resolve({ ok: true, json: async () => ({ token: "csrf-token" }) })
        : Promise.resolve({
            ok: true,
            text: async () => JSON.stringify({ token: "jwt-abc", username: "alice", role: "ROLE_ADMIN" }),
          }),
    );
    vi.stubGlobal("fetch", fetchMock);

    render(
      <AuthProvider>
        <LoginPage />
      </AuthProvider>,
    );

    await user.type(screen.getByPlaceholderText("Email hoặc tên đăng nhập"), "alice");
    await user.type(screen.getByPlaceholderText("Mật khẩu"), "secret");
    await user.click(screen.getByRole("button", { name: "Tiếp tục" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
    const [, init] = fetchMock.mock.calls.find((c) => String(c[0]).includes("/auth/login"))!;
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body)).toEqual({ username: "alice", password: "secret" });
    expect(init.headers["X-XSRF-TOKEN"]).toBe("csrf-token");
  });

  it("shows the backend error text when credentials are rejected", async () => {
    const user = userEvent.setup();
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        text: async () => "Email hoặc mật khẩu không đúng",
      }),
    );

    render(
      <AuthProvider>
        <LoginPage />
      </AuthProvider>,
    );

    await user.type(screen.getByPlaceholderText("Email hoặc tên đăng nhập"), "alice");
    await user.type(screen.getByPlaceholderText("Mật khẩu"), "wrong");
    await user.click(screen.getByRole("button", { name: "Tiếp tục" }));

    expect(await screen.findByText(/Email hoặc mật khẩu không đúng/)).toBeDefined();
  });

  it("switches to register mode and calls POST /api/auth/register", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.fn((url: RequestInfo) =>
      String(url).includes("/csrf")
        ? Promise.resolve({ ok: true, json: async () => ({ token: "csrf-token" }) })
        : Promise.resolve({
            ok: true,
            text: async () => JSON.stringify({ token: "jwt-new", username: "bob", role: "ROLE_VIEWER" }),
          }),
    );
    vi.stubGlobal("fetch", fetchMock);

    render(
      <AuthProvider>
        <LoginPage />
      </AuthProvider>,
    );

    await user.click(screen.getByText("Tạo tài khoản"));
    expect(screen.getAllByText("Tạo tài khoản").length).toBeGreaterThan(0);

    await user.type(screen.getByPlaceholderText("Email hoặc tên đăng nhập"), "bob");
    await user.type(screen.getByPlaceholderText("Mật khẩu"), "pw1234567890");
    await user.type(screen.getByPlaceholderText("Xác nhận mật khẩu"), "pw1234567890");
    await user.click(screen.getByRole("button", { name: "Tiếp tục" }));

    // CSRF token may be cached at module level from a previous test,
    // so total fetch count is 1 (POST only) or 2 (csrf bootstrap + POST).
    await waitFor(() =>
      expect(fetchMock.mock.calls.some((c) => String(c[0]) === "/api/auth/register")).toBe(true),
    );
  });

  it("shows password mismatch error in register mode", async () => {
    const user = userEvent.setup();
    render(
      <AuthProvider>
        <LoginPage />
      </AuthProvider>,
    );

    await user.click(screen.getByText("Tạo tài khoản"));
    await user.type(screen.getByPlaceholderText("Email hoặc tên đăng nhập"), "bob");
    await user.type(screen.getByPlaceholderText("Mật khẩu"), "pw1234567890");
    await user.type(screen.getByPlaceholderText("Xác nhận mật khẩu"), "different");
    await user.click(screen.getByRole("button", { name: "Tiếp tục" }));

    expect(await screen.findByText(/Mật khẩu xác nhận không khớp/)).toBeDefined();
  });

  it("shows password too short error in register mode", async () => {
    const user = userEvent.setup();
    render(
      <AuthProvider>
        <LoginPage />
      </AuthProvider>,
    );

    await user.click(screen.getByText("Tạo tài khoản"));
    await user.type(screen.getByPlaceholderText("Email hoặc tên đăng nhập"), "bob");
    await user.type(screen.getByPlaceholderText("Mật khẩu"), "short");
    await user.type(screen.getByPlaceholderText("Xác nhận mật khẩu"), "short");
    await user.click(screen.getByRole("button", { name: "Tiếp tục" }));

    expect(await screen.findByText(/Mật khẩu phải ít nhất 12 ký tự/)).toBeDefined();
  });
});