"""
Field Extraction Module

Extracts key-value document fields using a hybrid approach combining
regex pattern matching and spatial label anchoring.
"""

import re
from typing import List, Dict, Optional
from ._tokens import OCRWord


REGEX_PATTERNS: Dict[str, str] = {
    "invoice_no": r"(?:invoice\s*(?:no\.?|number|#)\s*[:\-]?\s*)([A-Za-z0-9\-\/]+)",
    "receipt_no": r"(?:receipt\s*(?:no\.?|number|#)\s*[:\-]?\s*)([A-Za-z0-9\-\/]+)",
    "certificate_id": r"(?:certificate\s*(?:no\.?|id|number)\s*[:\-]?\s*)([A-Za-z0-9\-\/]+)",
    "date": r"\b(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}|\d{4}[\/\-\.]\d{1,2}[\/\-\.]\d{1,2})\b",
    "total": r"(?:grand\s*total|total\s*amount|amount\s*due|total)\s*[:\-]?\s*(?:rs\.?|inr|\$|₹)?\s*([\d,]+\.\d{2}|[\d,]+)",
    "gstin": r"\b(\d{2}[A-Z]{5}\d{4}[A-Z]{1}\d[Z]{1}[A-Z\d]{1})\b",
    "pan": r"\b([A-Z]{5}\d{4}[A-Z])\b",
    "email": r"([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})",
    "phone": r"(?:\+?\d{1,3}[-.\s]?)?(\d{10})",
}


LABEL_FIELD_MAP: Dict[str, str] = {
    "vendor name": "vendor",
    "bill to": "customer",
    "customer name": "customer",
    "applicant name": "applicant_name",
    "name": "name",
    "issued by": "issued_by",
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
            start, end = match.span(1)
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
                label_words = label.split()
                for i in range(len(line) - len(label_words) + 1):
                    window = " ".join(w.text.lower() for w in line[i:i + len(label_words)])
                    if window == label or label in window:
                        remainder = [w for w in line[i + len(label_words):] if w.text not in (":", "-")]
                        if remainder:
                            results[field_name] = " ".join(w.text for w in remainder)
                        break
    return results


def extract_fields(full_text: str, words: List[OCRWord]) -> Dict[str, Optional[str]]:
    """Combine regex + label-anchor extraction into one field dictionary."""
    fields = {}
    fields.update(_extract_by_regex(full_text))
    fields.update(_extract_by_label_anchor(words))
    return fields

