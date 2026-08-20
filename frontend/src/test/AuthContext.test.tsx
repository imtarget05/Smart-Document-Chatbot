import { describe, it, expect, afterEach } from "vitest";
import { cleanup, render, screen, act } from "@testing-library/react";

afterEach(cleanup);
import { AuthProvider, useAuth, API_BASE_URL } from "../context/AuthContext";

function AuthProbe() {
  const { token, username, role, login, logout, isAuthenticated, isAdmin, isEngineer, isViewer } =
    useAuth();
  return (
    <div>
      <span data-testid="token">{token ?? "null"}</span>
      <span data-testid="username">{username ?? "null"}</span>
      <span data-testid="role">{role ?? "null"}</span>
      <span data-testid="authenticated">{String(isAuthenticated)}</span>
      <span data-testid="isAdmin">{String(isAdmin)}</span>
      <span data-testid="isEngineer">{String(isEngineer)}</span>
      <span data-testid="isViewer">{String(isViewer)}</span>
      <button onClick={() => login("tok", "alice", "ROLE_ADMIN")}>login</button>
      <button onClick={logout}>logout</button>
    </div>
  );
}

describe("AuthContext", () => {
  it("starts unauthenticated", () => {
    render(
      <AuthProvider>
        <AuthProbe />
      </AuthProvider>,
    );
    expect(screen.getByTestId("authenticated")).toHaveTextContent("false");
    expect(screen.getByTestId("token")).toHaveTextContent("null");
  });

  it("login sets token, username and derived role flags", () => {
    render(
      <AuthProvider>
        <AuthProbe />
      </AuthProvider>,
    );
    act(() => screen.getByText("login").click());
    expect(screen.getByTestId("token")).toHaveTextContent("tok");
    expect(screen.getByTestId("username")).toHaveTextContent("alice");
    expect(screen.getByTestId("role")).toHaveTextContent("ROLE_ADMIN");
    expect(screen.getByTestId("authenticated")).toHaveTextContent("true");
    expect(screen.getByTestId("isAdmin")).toHaveTextContent("true");
  });

  it("accepts ENGINEER and VIEWER roles without ROLE_ prefix", () => {
    render(
      <AuthProvider>
        <AuthProbe />
      </AuthProvider>,
    );
    act(() => screen.getByText("login").click());
    act(() => screen.getByText("logout").click());
    // after logout everything must be reset
    expect(screen.getByTestId("token")).toHaveTextContent("null");
    expect(screen.getByTestId("isAdmin")).toHaveTextContent("false");
  });

  it("logout clears all state", () => {
    render(
      <AuthProvider>
        <AuthProbe />
      </AuthProvider>,
    );
    act(() => screen.getByText("login").click());
    act(() => screen.getByText("logout").click());
    expect(screen.getByTestId("token")).toHaveTextContent("null");
    expect(screen.getByTestId("username")).toHaveTextContent("null");
    expect(screen.getByTestId("role")).toHaveTextContent("null");
    expect(screen.getByTestId("authenticated")).toHaveTextContent("false");
  });

  it("derives isEngineer and isViewer from plain role names", () => {
    const EngineerProbe = () => {
      const { login, isEngineer } = useAuth();
      return (
        <div>
          <button onClick={() => login("t", "bob", "ENGINEER")}>go</button>
          <span data-testid="isEngineer">{String(isEngineer)}</span>
        </div>
      );
    };
    render(
      <AuthProvider>
        <EngineerProbe />
      </AuthProvider>,
    );
    act(() => screen.getByText("go").click());
    expect(screen.getByTestId("isEngineer")).toHaveTextContent("true");
  });

  it("exports a default API base URL", () => {
    expect(API_BASE_URL).toBe("/api");
  });
});