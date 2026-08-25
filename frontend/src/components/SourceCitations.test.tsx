import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import SourceCitations from "./SourceCitations";
import EvidenceState from "./EvidenceState";
import type { SourceCitation } from "../types";

afterEach(cleanup);

const fullLegal: SourceCitation = {
  documentId: 7,
  content: "Người lao động làm việc theo hợp đồng...",
  score: 0.91,
  chunkId: 42,
  article: "35",
  clause: "1",
  point: "a",
  documentTitle: "Bộ luật Test",
  documentNumber: "01/2026/TEST",
  sourceType: "OFFICIAL",
};

function openCitations() {
  render(<SourceCitations sources={[fullLegal]} />);
  fireEvent.click(screen.getByTestId("citations-toggle"));
}

describe("SourceCitations", () => {
  it("renders full legal citation with article/clause/point", () => {
    openCitations();
    expect(screen.getByTestId("citation-title")).toHaveTextContent("Bộ luật Test");
    expect(screen.getByTestId("citation-number")).toHaveTextContent("01/2026/TEST");
    expect(screen.getByTestId("citation-location")).toHaveTextContent(
      "Điều 35 · Khoản 1 · Điểm a"
    );
    expect(screen.getByTestId("citation-source-type")).toHaveTextContent(
      "Văn bản chính thức"
    );
  });

  it("omits null metadata without fabricating anything", () => {
    const partial: SourceCitation = {
      content: "some text",
      documentTitle: null,
      article: null,
      clause: null,
      point: null,
      sourceType: "USER",
    };
    render(<SourceCitations sources={[partial]} />);
    fireEvent.click(screen.getByTestId("citations-toggle"));
    // Neutral label instead of an invented title
    expect(screen.getByTestId("citation-title")).toHaveTextContent(
      "Không xác định tên văn bản"
    );
    expect(screen.queryByTestId("citation-location")).toBeNull();
    expect(screen.queryByTestId("citation-number")).toBeNull();
    expect(screen.getByTestId("citation-source-type")).toHaveTextContent(
      "Tài liệu người dùng"
    );
  });

  it("labels FIXTURE sources as test data", () => {
    render(<SourceCitations sources={[{ ...fullLegal, sourceType: "FIXTURE" }]} />);
    fireEvent.click(screen.getByTestId("citations-toggle"));
    expect(screen.getByTestId("citation-source-type")).toHaveTextContent(
      "Dữ liệu kiểm thử"
    );
  });

  it("supports multiple sources preserving backend order", () => {
    render(
      <SourceCitations
        sources={[
          fullLegal,
          { ...fullLegal, chunkId: 43, article: "36" },
          { ...fullLegal, chunkId: 44, article: "37" },
        ]}
      />
    );
    expect(screen.getByTestId("citations-toggle")).toHaveTextContent(
      "Nguồn hỗ trợ (3)"
    );
    fireEvent.click(screen.getByTestId("citations-toggle"));
    const cards = screen.getAllByTestId("citation-location");
    expect(cards).toHaveLength(3);
    expect(cards[0]).toHaveTextContent("Điều 35");
    expect(cards[2]).toHaveTextContent("Điều 37");
  });

  it("'Xem nguồn' triggers navigation callback with the citation", () => {
    const onViewSource = vi.fn();
    render(<SourceCitations sources={[fullLegal]} onViewSource={onViewSource} />);
    fireEvent.click(screen.getByTestId("citations-toggle"));
    fireEvent.click(screen.getByTestId("view-source-0"));
    expect(onViewSource).toHaveBeenCalledWith(fullLegal);
  });

  it("falls back to legacy raw-chunk rendering when no structured sources", () => {
    render(<SourceCitations sources={null} sourceChunks="[doc] legacy text---[doc] more" />);
    expect(screen.queryByTestId("citations-toggle")).toBeNull();
    expect(screen.getByText(/legacy text/)).toBeInTheDocument();
  });
});

describe("EvidenceState", () => {
  it("shows truthful insufficient-evidence message for no_evidence", () => {
    render(<EvidenceState ragStrategy="no_evidence" confidence="low" />);
    const el = screen.getByTestId("evidence-state");
    expect(el).toHaveAttribute("data-state", "no_evidence");
    expect(el).toHaveTextContent(
      "Không tìm thấy đủ bằng chứng trong tài liệu hiện có"
    );
    expect(screen.queryByText(/AI không biết/i)).toBeNull();
  });

  it("shows evidence-backed state for direct strategy with high support", () => {
    render(<EvidenceState ragStrategy="direct" confidence="high" />);
    const el = screen.getByTestId("evidence-state");
    expect(el).toHaveAttribute("data-state", "direct");
    expect(el).toHaveTextContent("Dựa trên tài liệu được truy xuất");
    expect(el).toHaveTextContent("Mức độ hỗ trợ từ tài liệu: Cao");
  });

  it("shows low support without implying legal correctness percentages", () => {
    render(<EvidenceState ragStrategy="corrective" confidence="low" />);
    const el = screen.getByTestId("evidence-state");
    expect(el).toHaveTextContent("Thấp");
    expect(el.textContent).not.toMatch(/\d+%/);
    expect(el.textContent).not.toMatch(/chính xác pháp lý/i);
  });

  it("renders nothing for unknown/missing state", () => {
    const { container } = render(<EvidenceState ragStrategy={null} confidence={null} />);
    expect(container.querySelector('[data-testid="evidence-state"]')).toBeNull();
  });

  it("marks blocked requests as security blocks", () => {
    render(<EvidenceState ragStrategy="blocked" confidence={null} />);
    expect(screen.getByTestId("evidence-state")).toHaveAttribute("data-state", "blocked");
  });
});
