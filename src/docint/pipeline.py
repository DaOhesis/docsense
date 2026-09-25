"""OWNER: Lead. Glues all stages together. Keep this thin - logic lives in the stage modules."""
import uuid

from docint.classifier.doc_classifier import classify
from docint.extraction.extractor import extract
from docint.ocr.engine import run_ocr
from docint.preprocessing.preprocess import preprocess
from docint.schemas import DocumentResult
from docint.validation.rules import validate


def process_document(file_bytes: bytes, filename: str) -> DocumentResult:
    image = preprocess(file_bytes, filename)
    tokens = run_ocr(image)
    doc_type, type_conf = classify(tokens)
    fields, tables = extract(doc_type, tokens)
    validation, needs_review = validate(fields)
    return DocumentResult(
        doc_id=uuid.uuid4().hex,
        filename=filename,
        doc_type=doc_type,
        doc_type_conf=type_conf,
        ocr=tokens,
        fields=fields,
        tables=tables,
        validation=validation,
        needs_review=needs_review,
    )
