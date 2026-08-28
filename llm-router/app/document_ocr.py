"""
Document OCR + classification support for llm-router.

Cung cấp util extract text từ PDF/DOCX (dùng pdfplumber, python-docx),
và classify document type (PO/Invoice/ASN/Other) bằng heuristic keywords
trước khi gọi LLM model lớn.
"""

import io
import re
from typing import Optional

import pdfplumber
import docx


# ----------------------------------------------------------------------
# Text extraction
# ----------------------------------------------------------------------

def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract text from PDF using pdfplumber."""
    text_parts = []
    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
    except Exception as e:
        # Fallback: không extract được -> trả chuỗi rỗng
        return ""
    return "\n".join(text_parts)


def extract_text_from_docx(file_bytes: bytes) -> str:
    """Extract text from DOCX using python-docx."""
    try:
        doc = docx.Document(io.BytesIO(file_bytes))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n".join(paragraphs)
    except Exception:
        return ""


def extract_text(file_bytes: bytes, file_type: str) -> str:
    """Route extraction based on file_type."""
    if file_type == "pdf":
        return extract_text_from_pdf(file_bytes)
    elif file_type in ("docx", "doc"):
        return extract_text_from_docx(file_bytes)
    elif file_type == "txt":
        # Assume bytes are UTF-8 text
        return file_bytes.decode("utf-8", errors="replace")
    return ""


# ----------------------------------------------------------------------
# Document classification (heuristic keyword-based)
# ----------------------------------------------------------------------

# Purchase Order keywords
PO_KEYWORDS = [
    "purchase order", "đơn đặt hàng", "po #", "po number",
    "số đặt hàng", "đặt hàng", "order no", "order number",
    "vendor", "nhà cung cấp", "supplier", "đơn hàng mua",
]

# Invoice keywords
INVOICE_KEYWORDS = [
    "invoice", "hóa đơn", "inv #", "số hóa đơn", "số inv",
    "total amount", "tổng cộng", "thành tiền", "amount due",
    "bill to", "org-từ", "người mua", "người biên single",
    "hóa đơn điện tử", "e-invoice", "hoa don",
]

# ASN (Advanced Shipping Notice) keywords
ASN_KEYWORDS = [
    "asn", "advanced shipping notice", "lưu ý vận chuyển",
    "ship notice", "đón hàng", "ngày dự kiến giao",
    "shipping notice", "vận chuyển", "logic shipment",
    "expected delivery", "ngày giao hàng dự kiến",
]


def _contains_any(text: str, keywords: list[str]) -> bool:
    """Kiểm tra xem text có chứa bất kỳ keyword nào không (case-insensitive)."""
    lower = text.lower()
    return any(kw.lower() in lower for kw in keywords)


def classify_document_type(text: str, filename: str = "") -> str:
    """
    Phân loại document thành: PO, INVOICE, ASN, OTHER.
    Ưu tiên PO > Invoice > ASN > Other.

    Nếu text quá ngắn hoặc không detect được keyword, dùng heuristic từ filename.
    """
    lower_name = filename.lower()

    # 1. PO
    if _contains_any(text, PO_KEYWORDS):
        return "PO"
    if any(kw in lower_name for kw in ["po", "đặt", "đơn hàng", "purchase"]):
        return "PO"

    # 2. Invoice
    if _contains_any(text, INVOICE_KEYWORDS):
        return "INVOICE"
    if any(kw in lower_name for kw in ["inv", "hóa đơn", "invoice", "hoa don", "bill"]):
        return "INVOICE"

    # 3. ASN
    if _contains_any(text, ASN_KEYWORDS):
        return "ASN"
    if any(kw in lower_name for kw in ["asn", "ship", "vận chuyển", "shipping"]):
        return "ASN"

    return "OTHER"


# ----------------------------------------------------------------------
# Optional: gọi LLM model lớn để classify (nếu có)
# ----------------------------------------------------------------------

def classify_with_llm(text: str, filename: str = "", model_endpoint: Optional[str] = None) -> str:
    """
    Gọi LLM model (qua llm-router / Cloudflare / model endpoint) để classify.
    Nếu không có model endpoint, fallback về heuristic.

    Args:
        text: nội dung text đã extract
        filename: tên file gốc
        model_endpoint: URL endpoint LLM (ví dụ http://localhost:8010/classify)

    Returns:
        document_type: "PO", "INVOICE", "ASN", "OTHER"
    """
    if not model_endpoint:
        return classify_document_type(text, filename)

    # Gọi model endpoint (nếu có)
    import json
    import urllib.request
    import urllib.error

    payload = json.dumps({
        "text": text[:4000],  # Giới hạn độ dài
        "filename": filename,
    }).encode("utf-8")

    try:
        req = urllib.request.Request(
            model_endpoint,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            doc_type = result.get("document_type", "OTHER")
            if doc_type and doc_type.strip():
                return doc_type.strip().upper()
    except (urllib.error.URLError, json.JSONDecodeError, Exception) as e:
        # Fallback về heuristic nếu gọi model lỗi
        pass

    return classify_document_type(text, filename)
