"""
Field Extraction Module

Extracts key-value document fields using a hybrid approach combining
regex pattern matching and spatial label anchoring.
"""

import re
from typing import List, Dict, Optional
from ._tokens import OCRWord


REGEX_PATTERNS: Dict[str, str] = {
    "invoice_no": r"(?:\b(?:invoice\s*(?:no\b\.?|number\b|#)\s*[:\-]?\s*)([A-Za-z0-9\-\/]+)|\b(INV-[A-Za-z0-9\-\/]+)\b)",
    "receipt_no": r"\b(?:receipt\s*(?:no\b\.?|number\b|#)\s*[:\-]?\s*)([A-Za-z0-9\-\/]+)",
    "certificate_id": r"\b(?:certificate\s*(?:no\b\.?|id\b|number\b|#)\s*[:\-]?\s*)([A-Za-z0-9\-\/]+)",
    "date": r"\b(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}|\d{4}[\/\-\.]\d{1,2}[\/\-\.]\d{1,2})\b",
    "subtotal": r"(?:sub\s*total|subtotal)\s*[:\-]?\s*(?:rs\.?|inr|\$|₹)?\s*([\d,]+\.\d{2}|[\d,]+)",
    "tax": r"(?:tax|vat|gst)\s*[:\-]?\s*(?:rs\.?|inr|\$|₹)?\s*([\d,]+\.\d{2}|[\d,]+)",
    "total": r"(?:grand\s*total|total\s*amount|amount\s*due|\btotal)\s*[:\-]?\s*(?:rs\.?|inr|\$|₹)?\s*([\d,]+\.\d{2}|[\d,]+)",
    "gstin": r"\b(\d{2}[A-Z]{5}\d{4}[A-Z]{1}\d[Z]{1}[A-Z\d]{1})\b",
    "pan": r"\b([A-Z]{5}\d{4}[A-Z])\b",
    "email": r"([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})",
    "phone": r"(?:\+?\d{1,3}[-.\s]?)?(\d{10})",
    "issuer": r"(?:issued\s*by|issuer)\s*[:\-]?\s*([A-Za-z0-9\s.,&'\-]+?)(?:\s+(?:date|total|invoice|receipt)|\s*$)",
    "payment_method": r"(?:payment\s*(?:method)?\s*[:\-]?\s*|(?:paid\s*(?:by|with)|via)\s*[:\-]?\s*)([A-Za-z0-9\s]+?)(?:\s+(?:date|total|subtotal|tax|thank)|\s*$)",
}


LABEL_FIELD_MAP: Dict[str, str] = {
    "vendor name": "vendor",
    "vendor": "vendor",
    "bill to": "customer",
    "customer name": "customer",
    "applicant name": "applicant_name",
    "name": "name",
    "issued by": "issuer",
    "awarded to": "awarded_to",
    "date of birth": "date_of_birth",
    "address": "address",
    "payment method": "payment_method",
    "merchant": "merchant",
}


def _extract_by_regex(full_text: str) -> Dict[str, Optional[str]]:
    results: Dict[str, Optional[str]] = {}
    text_lower = full_text.lower()
    for field_name, pattern in REGEX_PATTERNS.items():
        match = re.search(pattern, text_lower, flags=re.IGNORECASE)
        if match:
            group_idx = match.lastindex if match.lastindex is not None else 1
            start, end = match.span(group_idx)
            results[field_name] = full_text[start:end]
        else:
            results[field_name] = None
    return results


def _line_up_words(words: List[OCRWord], y_tolerance: float = 8.0) -> List[List[OCRWord]]:
    """Group words into visual lines by similar y-position, sorted left to right."""
    sorted_words = sorted(words, key=lambda w: w.y_center)
    lines: List[List[OCRWord]] = []
    for w in sorted_words:
        placed = False
        for line in lines:
            avg_y = sum(lw.y_center for lw in line) / len(line)
            if abs(avg_y - w.y_center) <= y_tolerance:
                line.append(w)
                placed = True
                break
        if not placed:
            lines.append([w])
    for line in lines:
        line.sort(key=lambda w: w.x0)
    lines.sort(key=lambda line: sum(w.y_center for w in line) / len(line))
    return lines


def _extract_by_label_anchor(words: List[OCRWord]) -> Dict[str, Optional[str]]:
    results: Dict[str, Optional[str]] = {field: None for field in LABEL_FIELD_MAP.values()}
    lines = _line_up_words(words)

    for line in lines:
        line_text = " ".join(w.text for w in line).lower()
        for label, field_name in LABEL_FIELD_MAP.items():
            if label in line_text and results[field_name] is None:
                # 1. Single token prefix check (e.g. "Vendor: ACME Traders")
                matched = False
                for i, w in enumerate(line):
                    w_lower = w.text.lower()
                    if w_lower.startswith(label + ":") or w_lower.startswith(label + " -"):
                        val_part = re.sub(r"^" + re.escape(label) + r"[:\-]\s*", "", w.text, flags=re.IGNORECASE).strip()
                        following = [lw for lw in line[i + 1:] if lw.text not in (":", "-")]
                        full_val = (val_part + " " + " ".join(lw.text for lw in following)).strip()
                        if full_val:
                            results[field_name] = full_val
                            matched = True
                            break
                    elif w_lower.rstrip(":-") == label:
                        remainder = [lw for lw in line[i + 1:] if lw.text not in (":", "-")]
                        if remainder:
                            results[field_name] = " ".join(lw.text for lw in remainder)
                            matched = True
                            break
                # 2. Multi-word label window check (e.g. ["Awarded", "to:"])
                if not matched:
                    lbl_tokens = label.split()
                    n = len(lbl_tokens)
                    for i in range(len(line) - n + 1):
                        window_text = " ".join(w.text.lower().rstrip(":-") for w in line[i:i + n])
                        if window_text == label:
                            remainder = [lw for lw in line[i + n:] if lw.text not in (":", "-")]
                            if remainder:
                                results[field_name] = " ".join(lw.text for lw in remainder)
                                break
    return results


def extract_fields(full_text: str, words: List[OCRWord]) -> Dict[str, Optional[str]]:
    """Combine regex + label-anchor extraction into one field dictionary."""
    fields = _extract_by_regex(full_text)
    for k, v in _extract_by_label_anchor(words).items():
        if v is not None or k not in fields:
            fields[k] = v

    # Synchronize issued_by with issuer if present
    if fields.get("issuer"):
        fields["issued_by"] = fields["issuer"]

    # Positional heuristics for title and vendor/merchant when no explicit label exists
    lines = _line_up_words(words)
    if lines:
        first_line_text = " ".join(w.text for w in lines[0]).strip()
        # If top line is a document title (e.g. CERTIFICATE OF..., PATIENT INTAKE FORM...)
        if any(keyword in first_line_text.lower() for keyword in ("certificate", "form", "checklist")):
            if not fields.get("title"):
                # Title-case for clean representation
                fields["title"] = first_line_text.title()

        # If top line is an organization/vendor/merchant (e.g. Apex Industrial Supplies, Central Supermarket)
        # and not a generic word like INVOICE or RECEIPT
        for line in lines[:3]:
            cand = " ".join(w.text for w in line).strip()
            cand_lower = cand.lower()
            cand_words = set(re.findall(r"\b[a-z]+\b", cand_lower))
            excluded = {"invoice", "receipt", "date", "subtotal", "tax", "total"}
            if (
                cand
                and not cand_lower.startswith("inv-")
                and not cand_lower.startswith("issued by")
                and not (cand_words & excluded)
                and len(cand) > 3
            ):
                if not fields.get("vendor"):
                    fields["vendor"] = cand
                if not fields.get("merchant"):
                    fields["merchant"] = cand
                break

    # If merchant was found but vendor was not (or vice versa), align them
    if fields.get("merchant") and not fields.get("vendor"):
        fields["vendor"] = fields["merchant"]
    elif fields.get("vendor") and not fields.get("merchant"):
        fields["merchant"] = fields["vendor"]

    # Standalone payment method detection if no explicit label exists
    if not fields.get("payment_method"):
        for pm in ("visa card", "mastercard", "credit card", "debit card", "cash", "apple pay"):
            if pm in full_text.lower():
                fields["payment_method"] = pm.title()
                break

    return fields

