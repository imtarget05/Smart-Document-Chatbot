import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import DashboardPage from "./DashboardPage";

describe("DashboardPage", () => {
  it("renders the dashboard heading", () => {
    render(<DashboardPage />);

    expect(
      screen.getByRole("heading", { name: /Dashboard/i }),
    ).toBeInTheDocument();
  });
});
