# Data contract

Defined in `src/docint/schemas.py` (Pydantic). Every stage passes data in this shape.

```json
{
  "doc_id": "a1b2c3...",
  "filename": "invoice_001.png",
  "doc_type": "invoice",
  "doc_type_conf": 0.9,
  "ocr": [{"text": "INV-1024", "bbox": [10, 50, 120, 80], "conf": 0.95}],
  "fields": {
    "invoice_no": {"value": "INV-1024", "conf": 0.95, "bbox": null},
    "total": {"value": "1180.00", "conf": 0.93, "bbox": null}
  },
  "tables": [{"headers": ["item", "qty", "price"], "rows": [["Widget", "10", "100.00"]]}],
  "validation": [{"rule": "total_matches", "passed": true, "message": ""}],
  "needs_review": false
}
```

## Stage interfaces

| Stage | Function | Input → Output |
|---|---|---|
| Preprocess | `preprocess(file_bytes, filename)` | bytes → image (np.ndarray) |
| OCR | `run_ocr(image)` | image → `list[OCRToken]` |
| Classify | `classify(tokens)` | tokens → `(DocType, conf)` |
| Extract | `extract(doc_type, tokens)` | → `(dict[str, ExtractedField], list[Table])` |
| Validate | `validate(fields)` | → `(list[ValidationResult], needs_review)` |

## Standard field names (invoice)
`invoice_no, date, vendor, subtotal, tax, total, currency`

## Standard field names (receipt)
`merchant, date, total, payment_method`

Add fields for forms/certificates here as we decide them.

## Change process
Propose the change in the group chat, get a thumbs-up from all four, update this file and `schemas.py` in the same PR.
