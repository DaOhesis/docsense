# Initial task list (copy into GitHub Projects / Trello)

## Everyone (Week 1)
- [ ] Clone the repo, run `pytest`, start the API, upload a file at /docs
- [ ] Collect 10-15 anonymized real invoices/receipts each into `data/samples/`
- [ ] Read `docs/schema.md`

## Lead
- [ ] Download SROIE + CORD (receipts) and FUNSD (forms) datasets
- [ ] Create a labeled test set of ~30 documents (`data/labels/*.json` in the contract format)
- [ ] Write `docs/evaluation.md`: metrics (CER, field precision/recall/F1, % no-correction)
- [ ] Branch protection on `main` (require PR + 1 review)

## Person A: Preprocessing + OCR
- [ ] Load images and PDF pages into a numpy array
- [ ] Deskew + denoise + contrast enhancement
- [ ] Tesseract wrapper returning `list[OCRToken]`
- [ ] PaddleOCR wrapper returning `list[OCRToken]`
- [ ] Benchmark both on the samples -> `docs/ocr_benchmark.md`

## Person B: Classification + layout
- [ ] Label the samples by document type
- [ ] Keyword/rule baseline (already stubbed), measure accuracy
- [ ] TF-IDF + scikit-learn classifier on OCR text
- [ ] Region detection (header / key-value / table)

## Person C: Extraction + validation
- [ ] Invoice extractor: invoice_no, date, vendor, subtotal, tax, total (regex + position)
- [ ] Receipt extractor: merchant, date, total
- [ ] Line-item table extraction
- [ ] Validation rules: date format, required fields, line items sum == subtotal
- [ ] Confidence handling -> `needs_review`

## Person D: API + DB + UI
- [ ] Confirm upload -> process -> store -> fetch works with the mock pipeline
- [ ] Normalise DB tables (fields, line items) + PostgreSQL option
- [ ] Search filters: vendor, date range, amount range, doc_type, needs_review
- [ ] `PATCH /documents/{id}/fields` for human corrections
- [ ] Simple review UI (Streamlit or web): document image beside extracted fields
- [ ] Dockerfile + docker-compose (API + Postgres)
