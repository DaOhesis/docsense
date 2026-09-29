"""Dataset loader and benchmark annotation utilities for the evaluation framework.

Supports:
- Loading and saving ground-truth DocumentResult files (data/labels/*.json).
- Adapters for common public Document AI benchmarks:
    - SROIE (Scanned Receipts OCR and Information Extraction)
    - CORD (Consolidated Receipt Dataset)
    - FUNSD (Form Understanding in Noisy Scanned Documents)
- Synthetic ground-truth generator for testing pipeline evaluation offline.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from docint.schemas import DocType, DocumentResult, ExtractedField, OCRToken, Table


def load_labels(labels_dir: Path | str) -> dict[str, DocumentResult]:
    """Load all JSON label files from a directory into a map of filename -> DocumentResult."""
    path = Path(labels_dir)
    results: dict[str, DocumentResult] = {}
    if not path.exists():
        return results

    for file in sorted(path.glob("*.json")):
        try:
            content = file.read_text(encoding="utf-8")
            doc = DocumentResult.model_validate_json(content)
            results[file.stem] = doc
            if doc.filename:
                results[doc.filename] = doc
        except Exception:
            continue
    return results


def save_label(label: DocumentResult, target_path: Path | str) -> None:
    """Save a DocumentResult instance as a canonical ground-truth JSON file."""
    path = Path(target_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(label.model_dump_json(indent=2), encoding="utf-8")


def convert_sroie_sample(
    doc_id: str,
    filename: str,
    sroie_json: dict[str, str],
    ocr_lines: list[tuple[str, list[float]]] | None = None,
) -> DocumentResult:
    """Convert an SROIE ground-truth annotation to DocumentResult contract.

    SROIE format: {"company": "...", "date": "...", "address": "...", "total": "..."}
    """
    fields: dict[str, ExtractedField] = {}
    if "company" in sroie_json:
        fields["merchant"] = ExtractedField(value=sroie_json["company"], conf=1.0)
        fields["vendor"] = ExtractedField(value=sroie_json["company"], conf=1.0)
    if "date" in sroie_json:
        fields["date"] = ExtractedField(value=sroie_json["date"], conf=1.0)
    if "total" in sroie_json:
        fields["total"] = ExtractedField(value=sroie_json["total"], conf=1.0)
    if "address" in sroie_json:
        fields["address"] = ExtractedField(value=sroie_json["address"], conf=1.0)

    ocr_tokens: list[OCRToken] = []
    if ocr_lines:
        for text, bbox in ocr_lines:
            ocr_tokens.append(OCRToken(text=text, bbox=bbox, conf=1.0))

    return DocumentResult(
        doc_id=doc_id,
        filename=filename,
        doc_type=DocType.receipt,
        doc_type_conf=1.0,
        ocr=ocr_tokens,
        fields=fields,
        tables=[],
        validation=[],
        needs_review=False,
    )
