import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import AdminUsersPage from "./AdminUsersPage";

describe("AdminUsersPage", () => {
  it("renders the admin users heading", () => {
    const queryClient = new QueryClient();

    render(
      <QueryClientProvider client={queryClient}>
        <AdminUsersPage token="token" />
      </QueryClientProvider>,
    );

    expect(
      screen.getByRole("heading", { name: /Admin Users/i }),
    ).toBeInTheDocument();
  });
});
