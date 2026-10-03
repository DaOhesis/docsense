"""
test_validation.py

Unit tests for business rule validation module using sample field and table fixtures.
"""

import json
import os
from docint.extraction import extract
from docint.validation import validate

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def _load_fixture(filename):
    with open(os.path.join(FIXTURES_DIR, filename)) as f:
        return json.load(f)


def test_valid_invoice_passes():
    data = _load_fixture("invoice_tokens.json")
    fields, tables = extract(data["doc_type"], data["tokens"])
    results, needs_review = validate(data["doc_type"], fields, tables)

    assert needs_review is False
    assert all(r["passed"] for r in results)


def test_missing_required_field_flagged():
    fields = {
        "invoice_no": {"value": None, "conf": 0.0, "bbox": None},
        "date": {"value": "15/03/2026", "conf": 0.9, "bbox": None},
        "total": {"value": "500.00", "conf": 0.9, "bbox": None},
    }
    results, needs_review = validate("invoice", fields, [])

    assert needs_review is True
    assert any("invoice_no" in r["message"] for r in results)


def test_line_items_mismatch_flagged():
    fields = {
        "invoice_no": {"value": "INV-1", "conf": 0.9, "bbox": None},
        "date": {"value": "01/01/2026", "conf": 0.9, "bbox": None},
        "total": {"value": "999.00", "conf": 0.9, "bbox": None},  # doesn't match table sum
    }
    tables = [{"headers": ["item", "amount"], "rows": [["Widget", "100.00"], ["Gadget", "50.00"]]}]

    results, needs_review = validate("invoice", fields, tables)

    assert needs_review is True
    assert any("sum to" in r["message"] for r in results)


def test_future_date_flagged():
    fields = {
        "invoice_no": {"value": "INV-1", "conf": 0.9, "bbox": None},
        "date": {"value": "01/01/2099", "conf": 0.9, "bbox": None},
        "total": {"value": "100.00", "conf": 0.9, "bbox": None},
    }
    results, needs_review = validate("invoice", fields, [])

    assert needs_review is True
    assert any("future" in r["message"] for r in results)
