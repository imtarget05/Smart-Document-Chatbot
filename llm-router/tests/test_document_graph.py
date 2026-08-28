"""Tests cho document workflow agent (Phase 2)."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.document_graph import run_document_workflow  # noqa: E402

PO_TEXT = (
    "PURCHASE ORDER\nPO #PO-2024-001\nVendor: ABC Trading Corp\n"
    "Order date: 15/03/2024\nTotal amount: 1,500 USD"
)
INVOICE_TEXT = (
    "INVOICE\nSo hoa don: INV-2024-0099\nVendor: ABC Trading Corp\n"
    "Invoice date: 20/03/2024\nDue date: 20/04/2024\nTotal amount: 1,500 USD"
)


def test_classifies_po_and_extracts_fields():
    result = run_document_workflow(PO_TEXT, filename="po.pdf")
    assert result["doc_type"] == "PO"
    assert result["fields"]["po_number"] == "PO-2024-001"
    assert result["fields"]["vendor"] == "ABC Trading Corp"
    assert result["fields"]["total_amount"] == "1,500"
    assert result["fields"]["currency"] == "USD"
    assert "po_number" not in result["schema_mapping"]["missing"]


def test_schema_mapping_reports_missing_fields():
    result = run_document_workflow("PO #PO-1\nTotal amount: 10 USD", filename="po2.pdf")
    assert result["doc_type"] == "PO"
    assert "vendor" in result["schema_mapping"]["missing"]
    assert result["schema_mapping"]["mapped"]["po_number"] == "PO-1"


def test_po_invoice_match():
    po = run_document_workflow(PO_TEXT, filename="po.pdf")
    inv = run_document_workflow(
        INVOICE_TEXT, filename="inv.pdf",
        counterpart_fields=po["fields"],
    )
    assert inv["doc_type"] == "INVOICE"
    assert inv["match_status"] == "MATCHED"
    assert inv["match_detail"]["checks"]["amount_match"] is True
    assert inv["match_detail"]["checks"]["vendor_match"] is True


def test_mismatch_when_amounts_differ():
    inv = run_document_workflow(
        INVOICE_TEXT, filename="inv.pdf",
        counterpart_fields={"total_amount": "999 USD", "vendor": "XYZ Corp"},
    )
    assert inv["match_status"] == "MISMATCH"


def test_match_not_applicable_for_other():
    result = run_document_workflow("random note", filename="note.txt")
    assert result["match_status"] == "NOT_APPLICABLE"