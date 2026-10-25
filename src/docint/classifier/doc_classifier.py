from docint.classifier.ml_classifier import classify_ml
from docint.schemas import DocType, OCRToken


def classify_rules(tokens: list[OCRToken]) -> tuple[DocType, float]:
    """Tier 1: Fast heuristic keyword baseline."""
    if not tokens:
        return DocType.unknown, 0.0

    full_text = " ".join([t.text.lower() for t in tokens])

    if "invoice" in full_text or "bill to" in full_text:
        return DocType.invoice, 0.8

    receipt_keywords = (
        "receipt", "recibo", "total paid", "payment:", "cashier", "change due",
        "debit card", "credit card", "apple pay", "visa", "mastercard",
        "fare", "cab", "taxi", "trip", "ticket", "merchant", "nif", "iva",
        "thank you", "thanks for", "obrigado", "dinheiro", "troco",
    )
    if any(kw in full_text for kw in receipt_keywords):
        return DocType.receipt, 0.8
    elif "certificate" in full_text or "certify" in full_text or "awarded to" in full_text:
        return DocType.certificate, 0.8

    is_financial = any(kw in full_text for kw in ("total", "subtotal", "tax", "amount", "price", "eur", "$", "₹"))
    if "form" in full_text or "checklist" in full_text or ("signature:" in full_text and not is_financial):
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
