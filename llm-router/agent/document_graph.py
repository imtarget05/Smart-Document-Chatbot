"""Document workflow agent (Phase 2): classify -> extract -> map schema -> match.

LangGraph stateful pipeline cho document processing (PO / Invoice / ASN).
Mọi step đều deterministic-first (rule/regex), LLM chỉ là optional enhancement
— đảm bảo grounded, không hallucinate, chạy được không cần LLM.
"""

import re
from typing import Any, Dict, Optional, TypedDict

try:  # chạy như top-level package (uvicorn app.main:app từ llm-router/)
    from app import observability
    from app.document_ocr import classify_document_type
except ImportError:
    from ..app import observability
    from ..app.document_ocr import classify_document_type

from langgraph.graph import END, StateGraph

# ----------------------------------------------------------------------
# Schemas chuẩn cho từng loại document
# ----------------------------------------------------------------------
PO_SCHEMA = ["po_number", "vendor", "order_date", "total_amount", "currency"]
INVOICE_SCHEMA = ["invoice_number", "invoice_date", "due_date", "total_amount", "currency", "vendor"]
ASN_SCHEMA = ["asn_number", "ship_date", "expected_delivery", "carrier"]

SCHEMAS = {"PO": PO_SCHEMA, "INVOICE": INVOICE_SCHEMA, "ASN": ASN_SCHEMA}

# Regex extraction rules (deterministic, ưu tiên Vietnamese + English)
FIELD_PATTERNS = {
    "po_number": re.compile(r"(?:po\s*#|po\s*number|số\s*đặt\s*hàng)\s*[:#]?\s*([A-Z0-9\-/]+)", re.I),
    "invoice_number": re.compile(r"(?:invoice\s*(?:#|no\.?|number)|invoice\s*[:#]|số\s*hóa\s*đơn|so\s*hoa\s*don|so\s*hóa\s*đơn)\s*[:#]?\s*([A-Z0-9\-/]+)", re.I),
    "asn_number": re.compile(r"(?:asn\s*#|asn\s*number)\s*[:#]?\s*([A-Z0-9\-/]+)", re.I),
    "vendor": re.compile(r"(?:vendor|supplier|nhà\s*cung\s*cấp)\s*[:]?\s*([^\n,;]+)", re.I),
    "order_date": re.compile(r"(?:order\s*date|ngày\s*đặt)\s*[:]?\s*([\d/\-.]+)", re.I),
    "invoice_date": re.compile(r"(?:invoice\s*date|ngày\s*hóa\s*đơn)\s*[:]?\s*([\d/\-.]+)", re.I),
    "due_date": re.compile(r"(?:due\s*date|hạn\s*thanh\s*toán)\s*[:]?\s*([\d/\-.]+)", re.I),
    "ship_date": re.compile(r"(?:ship(?:ping)?\s*date|ngày\s*xuất\s*hàng)\s*[:]?\s*([\d/\-.]+)", re.I),
    "expected_delivery": re.compile(r"(?:expected\s*delivery|ngày\s*giao\s*hàng\s*dự\s*kiến)\s*[:]?\s*([\d/\-.]+)", re.I),
}
AMOUNT_PATTERN = re.compile(
    r"(?:total(?:\s*amount)?|tổng\s*cộng|thành\s*tiền|amount\s*due)\s*[:]?\s*"
    r"([\$€]?\s*[\d.,]+)\s*(USD|VND|EUR|usd|vnd|eur)?",
    re.I,
)


class DocumentState(TypedDict):
    text: str
    filename: str
    doc_type: str
    extracted_fields: Dict[str, Any]
    schema_mapping: Dict[str, Any]
    match_status: str
    match_detail: Dict[str, Any]
    confidence: float
    final_result: Dict[str, Any]


def classify_node(state: DocumentState) -> Dict[str, Any]:
    """Bước 1: classify PO/INVOICE/ASN/OTHER (heuristic từ document_ocr)."""
    _, obs = observability.span(None, "doc_classify", input={"filename": state.get("filename", "")})
    doc_type = classify_document_type(state.get("text", ""), state.get("filename", ""))
    observability.end_span(obs, output={"doc_type": doc_type})
    return {"doc_type": doc_type}


def extract_fields_node(state: DocumentState) -> Dict[str, Any]:
    """Bước 2: extract fields bằng regex rules (deterministic)."""
    _, obs = observability.span(None, "doc_extract", input={"doc_type": state.get("doc_type")})
    text = state.get("text", "")
    fields: Dict[str, Any] = {}
    for name, pattern in FIELD_PATTERNS.items():
        m = pattern.search(text)
        if m:
            fields[name] = m.group(1).strip()
    m = AMOUNT_PATTERN.search(text)
    if m:
        fields["total_amount"] = m.group(1).strip()
        fields["currency"] = (m.group(2) or "USD").upper()
    confidence = round(min(1.0, len(fields) / 4), 2) if fields else 0.0
    observability.end_span(obs, output={"fields_found": list(fields)})
    return {"extracted_fields": fields, "confidence": confidence}


def map_schema_node(state: DocumentState) -> Dict[str, Any]:
    """Bước 3: map extracted fields vào schema chuẩn của doc_type."""
    doc_type = state.get("doc_type", "OTHER")
    schema = SCHEMAS.get(doc_type, [])
    extracted = state.get("extracted_fields", {})
    mapping = {
        "schema": schema,
        "mapped": {k: extracted[k] for k in schema if k in extracted},
        "missing": [k for k in schema if k not in extracted],
        "extra": [k for k in extracted if k not in schema],
    }
    return {"schema_mapping": mapping}
    confidence: float
    final_result: Dict[str, Any]


def _num(value: Any) -> Optional[float]:
    try:
        return float(str(value).replace(",", "").replace("$", "").replace("€", ""))
    except (TypeError, ValueError):
        return None


def match_node(state: DocumentState) -> Dict[str, Any]:
    """Bước 4: match PO ↔ Invoice (nếu state có counterpart_fields)."""
    doc_type = state.get("doc_type")
    counterpart = state.get("match_detail", {}).get("counterpart_fields") or {}
    if doc_type not in ("PO", "INVOICE") or not counterpart:
        return {"match_status": "NOT_APPLICABLE", "match_detail": {}}

    checks: Dict[str, Any] = {}
    amount_a = _num(state.get("extracted_fields", {}).get("total_amount"))
    amount_b = _num(counterpart.get("total_amount"))
    if amount_a is not None and amount_b is not None:
        diff = abs(amount_a - amount_b)
        checks["amount_match"] = diff <= max(0.01, amount_a * 0.01)
        checks["amount_diff"] = diff
    vendor_a = (state.get("extracted_fields", {}).get("vendor") or "").lower().strip()
    vendor_b = (counterpart.get("vendor") or "").lower().strip()
    if vendor_a and vendor_b:
        checks["vendor_match"] = vendor_a in vendor_b or vendor_b in vendor_a

    matched = bool(checks) and all(v is True for v in checks.values() if isinstance(v, bool))
    status = "MATCHED" if matched else ("MISMATCH" if checks else "INSUFFICIENT_DATA")
    return {"match_status": status, "match_detail": {"checks": checks}}


def output_node(state: DocumentState) -> Dict[str, Any]:
    return {
        "final_result": {
            "doc_type": state.get("doc_type"),
            "fields": state.get("extracted_fields", {}),
            "schema_mapping": state.get("schema_mapping", {}),
            "match_status": state.get("match_status", "NOT_APPLICABLE"),
            "match_detail": state.get("match_detail", {}),
            "confidence": state.get("confidence", 0.0),
        }
    }


def build_document_app():
    graph = StateGraph(DocumentState)
    graph.add_node("classify", classify_node)
    graph.add_node("extract", extract_fields_node)
    graph.add_node("map_schema", map_schema_node)
    graph.add_node("match", match_node)
    graph.add_node("output", output_node)
    graph.set_entry_point("classify")
    graph.add_edge("classify", "extract")
    graph.add_edge("extract", "map_schema")
    graph.add_edge("map_schema", "match")
    graph.add_edge("match", "output")
    graph.add_edge("output", END)
    return graph.compile()


document_app = build_document_app()


def run_document_workflow(
    text: str,
    filename: str = "",
    counterpart_fields: Optional[Dict[str, Any]] = None,
    trace_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Chạy document workflow; trả final_result dict."""
    initial: DocumentState = {
        "text": text or "",
        "filename": filename or "",
        "doc_type": "",
        "extracted_fields": {},
        "schema_mapping": {},
        "match_status": "NOT_APPLICABLE",
        "match_detail": {"counterpart_fields": counterpart_fields or {}},
        "confidence": 0.0,
        "final_result": {},
    }
    result = document_app.invoke(initial)
    _, obs = observability.span(trace_id, "doc_workflow", input={"filename": filename})
    observability.end_span(obs, output={"doc_type": result.get("doc_type")})
    return result["final_result"]