import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AuthProvider } from "../context/AuthContext";
import UserMenu from "./UserMenu";

afterEach(cleanup);

describe("UserMenu", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  function renderUserMenu(props: { username?: string | null; role?: string | null; onLogout?: () => void } = {}) {
    return render(
      <AuthProvider>
        <UserMenu
          username={props.username}
          role={props.role}
          onLogout={props.onLogout ?? vi.fn()}
        />
      </AuthProvider>,
    );
  }

  it("renders user initials in the button", () => {
    renderUserMenu({ username: "John Doe" });
    expect(screen.getByRole("button", { name: "Menu người dùng" })).toHaveTextContent("JO");
  });

  it("shows username and role label when dropdown opens", async () => {
    const user = userEvent.setup();
    renderUserMenu({ username: "Alice Engineer", role: "ROLE_ENGINEER" });

    await user.click(screen.getByRole("button", { name: "Menu người dùng" }));

    await waitFor(() => expect(screen.getByText("Alice Engineer")).toBeInTheDocument());
    expect(screen.getByText("Kỹ sư")).toBeInTheDocument();
  });

  it("maps ADMIN role to 'Quản trị viên'", async () => {
    const user = userEvent.setup();
    renderUserMenu({ role: "ROLE_ADMIN" });

    await user.click(screen.getByRole("button", { name: "Menu người dùng" }));

    await waitFor(() => expect(screen.getByText("Quản trị viên")).toBeInTheDocument());
  });

  it("maps VIEWER role to 'Người xem'", async () => {
    const user = userEvent.setup();
    renderUserMenu({ role: "ROLE_VIEWER" });

    await user.click(screen.getByRole("button", { name: "Menu người dùng" }));

    await waitFor(() => expect(screen.getByText("Người xem")).toBeInTheDocument());
  });

  it("maps ENGINEER role to 'Kỹ sư'", async () => {
    const user = userEvent.setup();
    renderUserMenu({ role: "ROLE_ENGINEER" });

    await user.click(screen.getByRole("button", { name: "Menu người dùng" }));

    await waitFor(() => expect(screen.getByText("Kỹ sư")).toBeInTheDocument());
  });

  it("toggles dropdown open/closed on button click", async () => {
    const user = userEvent.setup();
    renderUserMenu();

    const button = screen.getByRole("button", { name: "Menu người dùng" });
    expect(button).toHaveAttribute("aria-expanded", "false");

    await user.click(button);
    expect(button).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByText("Đăng xuất")).toBeInTheDocument();

    await user.click(button);
    expect(button).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByText("Đăng xuất")).not.toBeInTheDocument();
  });

  it("calls onLogout and closes dropdown when logout clicked", async () => {
    const user = userEvent.setup();
    const onLogout = vi.fn();
    renderUserMenu({ onLogout });

    await user.click(screen.getByRole("button", { name: "Menu người dùng" }));
    await user.click(screen.getByRole("button", { name: "Đăng xuất" }));

    expect(onLogout).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("button", { name: "Menu người dùng" })).toHaveAttribute("aria-expanded", "false");
  });

  it("closes dropdown on outside click", async () => {
    const user = userEvent.setup();
    renderUserMenu();

    await user.click(screen.getByRole("button", { name: "Menu người dùng" }));
    expect(screen.getByRole("button", { name: "Menu người dùng" })).toHaveAttribute("aria-expanded", "true");

    await user.click(document.body);
    expect(screen.getByRole("button", { name: "Menu người dùng" })).toHaveAttribute("aria-expanded", "false");
  });

  it("shows single initial when username is one character", () => {
    renderUserMenu({ username: "A" });
    expect(screen.getByRole("button", { name: "Menu người dùng" })).toHaveTextContent("A");
  });

  it("shows default 'U' when username is null", () => {
    renderUserMenu({ username: null });
    expect(screen.getByRole("button", { name: "Menu người dùng" })).toHaveTextContent("U");
  });

  it("shows default 'U' when username is empty string", () => {
    renderUserMenu({ username: "" });
    expect(screen.getByRole("button", { name: "Menu người dùng" })).toHaveTextContent("U");
  });

  it("handles role without ROLE_ prefix", async () => {
    const user = userEvent.setup();
    renderUserMenu({ role: "ADMIN" });

    await user.click(screen.getByRole("button", { name: "Menu người dùng" }));

    await waitFor(() => expect(screen.getByText("Quản trị viên")).toBeInTheDocument());
  });

  it("shows null role label when role is unknown", async () => {
    const user = userEvent.setup();
    renderUserMenu({ role: "UNKNOWN_ROLE" });

    await user.click(screen.getByRole("button", { name: "Menu người dùng" }));

    await waitFor(() => expect(screen.queryByText("Quản trị viên")).not.toBeInTheDocument());
    expect(screen.queryByText("Kỹ sư")).not.toBeInTheDocument();
    expect(screen.queryByText("Người xem")).not.toBeInTheDocument();
  });
});