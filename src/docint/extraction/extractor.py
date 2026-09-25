"""OWNER: Person C  |  Branch prefix: feature/extract-*

TODO:
  - one extractor per DocType (start with invoice + receipt)
  - regex + bbox-position rules first, ML/NER layer later
  - table extraction for line items
"""
from docint.schemas import DocType, ExtractedField, OCRToken, Table


def extract(doc_type: DocType, tokens: list[OCRToken]) -> tuple[dict[str, ExtractedField], list[Table]]:
    """Return (fields, tables). STUB: returns fixed dummy invoice data."""
    fields = {
        "invoice_no": ExtractedField(value="INV-1024", conf=0.95),
        "date": ExtractedField(value="2026-09-01", conf=0.90),
        "vendor": ExtractedField(value="ACME Traders", conf=0.85),
        "subtotal": ExtractedField(value="1000.00", conf=0.92),
        "tax": ExtractedField(value="180.00", conf=0.92),
        "total": ExtractedField(value="1180.00", conf=0.93),
    }
    tables = [Table(headers=["item", "qty", "price"], rows=[["Widget", "10", "100.00"]])]
    return fields, tables
