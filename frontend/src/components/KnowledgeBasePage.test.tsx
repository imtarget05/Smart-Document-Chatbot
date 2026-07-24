import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import KnowledgeBasePage from "./KnowledgeBasePage";

describe("KnowledgeBasePage", () => {
  it("renders the knowledge base heading", () => {
    render(<KnowledgeBasePage />);

    expect(
      screen.getByRole("heading", { name: /Knowledge Base/i }),
    ).toBeInTheDocument();
  });
});
