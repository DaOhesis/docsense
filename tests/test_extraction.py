"""
 test_extraction.py
 
 Unit tests for field and table extraction module using sample OCR fixtures.  
"""

import json  
import os
from docint.extraction import extract

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def _load_fixture(filename):
    with open(os.path.join(FIXTURES_DIR, filename)) as f:
        return json.load(f)

data = _load_fixture("form_tokens.json")

def test_invoice_fields_extracted():
    data = _load_fixture("invoice_tokens.json")
    fields, tables = extract(data["doc_type"], data["tokens"])

    assert fields["invoice_no"]["value"] == "INV-2026-0451"
    assert fields["date"]["value"] == "15/03/2026"
    assert fields["total"]["value"] == "500.00"
    assert fields["gstin"]["value"] == "29ABCDE1234F1Z5"


def test_invoice_table_extracted():
    data = _load_fixture("invoice_tokens.json")
    fields, tables = extract(data["doc_type"], data["tokens"])

    assert len(tables) == 1
    assert "amount" in tables[0]["headers"]
    assert len(tables[0]["rows"]) == 2  # Widget A, Widget B


def test_receipt_fields_extracted():
    data = _load_fixture("receipt_tokens.json")
    fields, tables = extract(data["doc_type"], data["tokens"])

    assert fields["receipt_no"]["value"] == "RCPT-88213"
    assert fields["total"]["value"] == "115.00"


def test_certificate_fields_extracted():
    data = _load_fixture("certificate_tokens.json")
    fields, tables = extract(data["doc_type"], data["tokens"])

    assert fields["awarded_to"]["value"] == "Arjun Nair"
    assert fields["certificate_id"]["value"] == "CERT-2026-9981"


def test_missing_field_is_none_not_absent():
    """A field regex/label-anchor can't find should be None, not missing from the dict."""
    data = _load_fixture("form_tokens.json")
    fields, tables = extract(data["doc_type"], data["tokens"])

    assert "gstin" in fields
    assert fields["gstin"]["value"] is None

def test_extract_invoice():
    data = _load_fixture("form_tokens.json")
    fields, tables = extract("form", data["tokens"])
    print("\n--- EXTRACTED FIELDS ---")
    print(fields)
    print("------------------------")
    assert fields is not None

