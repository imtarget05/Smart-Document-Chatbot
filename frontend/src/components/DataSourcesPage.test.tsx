import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import DataSourcesPage from "./DataSourcesPage";

describe("DataSourcesPage", () => {
  it("renders the data sources workspace", () => {
    const queryClient = new QueryClient();

    render(
      <QueryClientProvider client={queryClient}>
        <DataSourcesPage token="token" />
      </QueryClientProvider>,
    );

    expect(screen.getByText(/Data Sources/i)).toBeInTheDocument();
  });
});
