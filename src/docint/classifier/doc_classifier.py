"""OWNER: Person B  |  Branch prefix: feature/classifier-*

TODO:
  - baseline: keyword rules or TF-IDF + scikit-learn on OCR text
  - later (only if needed): small PyTorch model on page images
  - layout analysis: detect header / key-value / table regions
"""
from docint.schemas import DocType, OCRToken


def classify(tokens: list[OCRToken]) -> tuple[DocType, float]:
    """Return (doc_type, confidence). STUB: keyword baseline."""
    text = " ".join(t.text.lower() for t in tokens)
    if "invoice" in text:
        return DocType.invoice, 0.9
    if "receipt" in text:
        return DocType.receipt, 0.9
    if "certificate" in text:
        return DocType.certificate, 0.9
    return DocType.unknown, 0.3
