import type { RagStrategy } from "../types";

interface Props {
  ragStrategy?: RagStrategy | null;
  confidence?: string | null;
}

/**
 * Truthful evidence-state banner for an answer (Decision 14).
 *
 * - "no_evidence" is shown as insufficient evidence, NOT as "AI doesn't know".
 * - Confidence maps to document-support language; the raw number is never
 *   presented as a percentage of legal correctness.
 */
export default function EvidenceState({ ragStrategy, confidence }: Props) {
  if (!ragStrategy) return null;

  if (ragStrategy === "no_evidence") {
    return (
      <div
        className="mt-2 inline-flex items-center gap-1.5 text-[11px] px-2 py-1 rounded-lg bg-orange-50 border border-orange-200 text-orange-700"
        data-testid="evidence-state"
        data-state="no_evidence"
      >
        <span>⚠️</span>
        Không tìm thấy đủ bằng chứng trong tài liệu hiện có. Câu trả lời không dựa trên
        văn bản được truy xuất.
      </div>
    );
  }

  if (ragStrategy === "blocked") {
    return (
      <div
        className="mt-2 inline-flex items-center gap-1.5 text-[11px] px-2 py-1 rounded-lg bg-red-50 border border-red-200 text-red-700"
        data-testid="evidence-state"
        data-state="blocked"
      >
        <span>🚫</span> Yêu cầu đã bị chặn vì lý do bảo mật.
      </div>
    );
  }

  const supportLabel =
    confidence === "high"
      ? "Cao"
      : confidence === "medium"
        ? "Trung bình"
        : confidence === "low"
          ? "Thấp"
          : null;

  return (
    <div
      className="mt-2 inline-flex items-center gap-1.5 text-[11px] px-2 py-1 rounded-lg bg-blue-50 border border-blue-100 text-blue-700"
      data-testid="evidence-state"
      data-state={ragStrategy}
    >
      <span>✅</span>
      Dựa trên tài liệu được truy xuất
      {supportLabel && (
        <>
          {" · "}Mức độ hỗ trợ từ tài liệu: {supportLabel}
        </>
      )}
      {ragStrategy === "corrective" && " (đã tinh chỉnh truy vấn)"}
      {ragStrategy === "web_search" && " (có sử dụng kết quả web)"}
    </div>
  );
}
