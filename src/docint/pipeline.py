"""OWNER: Lead. Glues all stages together. Keep this thin - logic lives in the stage modules."""
from __future__ import annotations

import logging
import time
import uuid

from docint.classifier.doc_classifier import classify
from docint.extraction.extractor import extract
from docint.ocr.engine import run_ocr
from docint.preprocessing.preprocess import preprocess
from docint.schemas import DocumentResult
from docint.validation.rules import validate

logger = logging.getLogger("docint.pipeline")


def process_document(file_bytes: bytes, filename: str) -> DocumentResult:
    """Execute the full document intelligence pipeline:

    Upload -> Preprocess -> OCR -> Classify -> Extract -> Validate -> DocumentResult
    """
    doc_id = uuid.uuid4().hex
    safe_filename = filename.strip() if filename else "untitled"

    logger.info("Processing document %s (filename=%s, size=%d bytes)", doc_id, safe_filename, len(file_bytes))
    t0 = time.perf_counter()

    # 1. Preprocessing (image decoding, deskewing, enhancement)
    t_start = time.perf_counter()
    image = preprocess(file_bytes, safe_filename)
    t_preprocess = (time.perf_counter() - t_start) * 1000.0

    # 2. OCR (word/line tokenization with coordinates & confidence)
    t_start = time.perf_counter()
    tokens = run_ocr(image)
    t_ocr = (time.perf_counter() - t_start) * 1000.0

    # 3. Document Classification (invoice, receipt, form, certificate, unknown)
    t_start = time.perf_counter()
    doc_type, type_conf = classify(tokens)
    t_classify = (time.perf_counter() - t_start) * 1000.0

    # 4. Key Information & Table Extraction
    t_start = time.perf_counter()
    fields, tables = extract(doc_type, tokens)
    t_extract = (time.perf_counter() - t_start) * 1000.0

    # 5. Rule-based Validation & Review Flagging
    t_start = time.perf_counter()
    validation, needs_review = validate(fields)
    t_validate = (time.perf_counter() - t_start) * 1000.0

    total_ms = (time.perf_counter() - t0) * 1000.0
    logger.info(
        "Document %s finished in %.1f ms (preprocess: %.1fms, ocr: %.1fms, classify: %.1fms, extract: %.1fms, validate: %.1fms, doc_type: %s, needs_review: %s)",
        doc_id,
        total_ms,
        t_preprocess,
        t_ocr,
        t_classify,
        t_extract,
        t_validate,
        doc_type.value,
        needs_review,
    )

    return DocumentResult(
        doc_id=doc_id,
        filename=safe_filename,
        doc_type=doc_type,
        doc_type_conf=type_conf,
        ocr=tokens,
        fields=fields,
        tables=tables,
        validation=validation,
        needs_review=needs_review,
    )
