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
        className="mt-2 inline-flex items-center gap-1.5 text-[11px] px-2.5 py-1.5 rounded-material-full bg-[#fef7e0] border border-[#fde293] text-[#b06000]"
        data-testid="evidence-state"
        data-state="no_evidence"
      >
        <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
          <path d="M1 21h22L12 2 1 21zm12-3h-2v-2h2v2zm0-4h-2v-4h2v4z" />
        </svg>
        Không tìm thấy đủ bằng chứng trong tài liệu hiện có. Câu trả lời không dựa trên
        văn bản được truy xuất.
      </div>
    );
  }

  if (ragStrategy === "blocked") {
    return (
      <div
        className="mt-2 inline-flex items-center gap-1.5 text-[11px] px-2.5 py-1.5 rounded-material-full bg-[#fce8e6] border border-[#f5c6cb] text-[#a50e0e]"
        data-testid="evidence-state"
        data-state="blocked"
      >
        <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
          <path d="M12 2L1 21h22L12 2zm0 14a1 1 0 110 2 1 1 0 010-2zm1-8h-2v6h2V8z" />
        </svg>
        Yêu cầu đã bị chặn vì lý do bảo mật.
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
      className="mt-2 inline-flex items-center gap-1.5 text-[11px] px-2.5 py-1.5 rounded-material-full bg-[#e6f4ea] border border-[#34a853]/30 text-[#137333]"
      data-testid="evidence-state"
      data-state={ragStrategy}
    >
      <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
        <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z" />
      </svg>
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
