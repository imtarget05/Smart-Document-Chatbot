import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import MessageBubble from "./MessageBubble";

vi.mock("rehype-highlight", () => ({
  default: () => ({}),
}));

describe("MessageBubble", () => {
  it("renders user message as plain text", () => {
    render(<MessageBubble content="Hello world" role="user" />);
    expect(screen.getByText("Hello world")).toBeDefined();
  });

  it("renders assistant message with markdown heading", () => {
    render(<MessageBubble content="# Heading" role="assistant" />);
    expect(screen.getByText("Heading", { selector: "h1" })).toBeDefined();
  });

  it("renders bold text", () => {
    render(<MessageBubble content="**bold text**" role="assistant" />);
    expect(screen.getByText("bold text", { selector: "strong" })).toBeDefined();
  });

  it("renders italic text", () => {
    render(<MessageBubble content="*italic text*" role="assistant" />);
    expect(screen.getByText("italic text", { selector: "em" })).toBeDefined();
  });

  it("renders unordered list items", () => {
    render(<MessageBubble content="- item 1\n- item 2" role="assistant" />);
    const lists = screen.getAllByRole("list");
    expect(lists.length).toBeGreaterThan(0);
    expect(screen.getByText(/item 1/)).toBeDefined();
    expect(screen.getByText(/item 2/)).toBeDefined();
  });

  it("renders ordered list items", () => {
    render(<MessageBubble content="1. first\n2. second" role="assistant" />);
    const lists = screen.getAllByRole("list");
    expect(lists.length).toBeGreaterThan(0);
    expect(screen.getByText(/first/)).toBeDefined();
    expect(screen.getByText(/second/)).toBeDefined();
  });

  it("renders inline code", () => {
    render(<MessageBubble content="Use `console.log()`" role="assistant" />);
    expect(screen.getByText("console.log()", { selector: "code" })).toBeDefined();
  });

  it("renders code block", () => {
    render(<MessageBubble content="```js\nconst x = 1;\n```" role="assistant" />);
    const codeBlocks = screen.getAllByText(/const x = 1/);
    expect(codeBlocks.length).toBeGreaterThan(0);
  });

  it("renders table (GFM)", () => {
    const table = "| A | B |\n|---|---|\n| 1 | 2 |";
    render(<MessageBubble content={table} role="assistant" />);
    expect(screen.getByText("A", { selector: "th" })).toBeDefined();
    expect(screen.getByText("1", { selector: "td" })).toBeDefined();
  });

  it("renders link with target blank", () => {
    render(<MessageBubble content="[click here](https://example.com)" role="assistant" />);
    const link = screen.getByText("click here");
    expect(link.tagName).toBe("A");
    expect(link.getAttribute("target")).toBe("_blank");
    expect(link.getAttribute("rel")).toBe("noopener noreferrer");
  });

  it("renders typing indicator when content is empty", () => {
    render(<MessageBubble content="" role="assistant" />);
    expect(screen.getByRole("status")).toBeDefined();
    expect(screen.getByLabelText("Đang trả lời")).toBeDefined();
  });

  it("sets aria-live polite when streaming", () => {
    const { container } = render(<MessageBubble content="streaming..." role="assistant" isStreaming />);
    const markdownBody = container.querySelector(".markdown-body");
    expect(markdownBody?.getAttribute("aria-live")).toBe("polite");
  });

  it("does not set aria-live when not streaming", () => {
    const { container } = render(<MessageBubble content="done" role="assistant" />);
    const markdownBody = container.querySelector(".markdown-body");
    expect(markdownBody?.getAttribute("aria-live")).toBeNull();
  });
});
