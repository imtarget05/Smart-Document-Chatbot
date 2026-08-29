import type { SourceCitation } from "../types";

export const SOURCE_TYPE_LABELS: Record<string, string> = {
  OFFICIAL: "Văn bản chính thức",
  USER: "Tài liệu người dùng",
  FIXTURE: "Dữ liệu kiểm thử",
};

/** Builds "Điều N · Khoản M · Điểm K" from only the levels actually present. */
export function locationLabel(s: SourceCitation): string | null {
  const parts: string[] = [];
  if (s.article) parts.push(`Điều ${s.article}`);
  if (s.clause) parts.push(`Khoản ${s.clause}`);
  if (s.point) parts.push(`Điểm ${s.point}`);
  return parts.length > 0 ? parts.join(" · ") : null;
}
