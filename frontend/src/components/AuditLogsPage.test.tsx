import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import AuditLogsPage from "./AuditLogsPage";

describe("AuditLogsPage", () => {
  it("renders the audit logs heading", () => {
    const queryClient = new QueryClient();

    render(
      <QueryClientProvider client={queryClient}>
        <AuditLogsPage token="token" />
      </QueryClientProvider>,
    );

    expect(
      screen.getByRole("heading", { name: /Audit Logs/i }),
    ).toBeInTheDocument();
  });
});
