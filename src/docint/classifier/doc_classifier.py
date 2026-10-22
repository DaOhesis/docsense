from docint.classifier.ml_classifier import classify_ml
from docint.schemas import DocType, OCRToken


def classify_rules(tokens: list[OCRToken]) -> tuple[DocType, float]:
    """Tier 1: Fast heuristic keyword baseline."""
    if not tokens:
        return DocType.unknown, 0.0

    full_text = " ".join([t.text.lower() for t in tokens])

    if "invoice" in full_text or "bill to" in full_text:
        return DocType.invoice, 0.8
    elif (
        "receipt" in full_text
        or "total paid" in full_text
        or "payment:" in full_text
        or "cashier" in full_text
        or "change due" in full_text
        or "debit card" in full_text
        or "credit card" in full_text
        or "apple pay" in full_text
        or "visa" in full_text
        or "mastercard" in full_text
    ):
        return DocType.receipt, 0.8
    elif "certificate" in full_text or "certify" in full_text:
        return DocType.certificate, 0.8
    elif "form" in full_text or "signature:" in full_text or "checklist" in full_text:
        return DocType.form, 0.6

    return DocType.unknown, 0.1


def classify(tokens: list[OCRToken]) -> tuple[DocType, float]:
    """
    Main pipeline entry point for Area B.
    Uses fast keyword rules first; falls back to TF-IDF + Logistic Regression ML model.
    """
    if not tokens:
        return DocType.unknown, 0.0

    # 1. Try fast deterministic keyword rules first
    doc_type, conf = classify_rules(tokens)
    if doc_type != DocType.unknown:
        return doc_type, conf

    # 2. Fallback to statistical ML classifier if no exact keywords matched
    ml_type, ml_conf = classify_ml(tokens)
    if ml_type != DocType.unknown:
        return ml_type, ml_conf

    return DocType.unknown, 0.1
