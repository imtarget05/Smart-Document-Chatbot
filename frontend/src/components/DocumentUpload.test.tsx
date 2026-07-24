import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import DocumentUpload from "./DocumentUpload";

function renderUpload() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  render(
    <QueryClientProvider client={queryClient}>
      <DocumentUpload onDocumentUploaded={vi.fn()} />
    </QueryClientProvider>,
  );
}

describe("DocumentUpload", () => {
  it("rejects an unsupported file before sending a request", async () => {
    renderUpload();
    const request = vi.spyOn(globalThis, "fetch");
    const input = screen.getByLabelText(/upload document/i) as HTMLInputElement;

    await userEvent.upload(
      input,
      new File(["bad"], "payload.exe", { type: "application/octet-stream" }),
    );

    expect(
      screen.getByText("Only PDF, DOCX, and TXT files are supported"),
    ).toBeInTheDocument();
    expect(request).not.toHaveBeenCalled();
    request.mockRestore();
  });
});
