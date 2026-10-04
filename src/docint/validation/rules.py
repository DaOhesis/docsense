
"""
Validation Rules Engine

Applies business logic, required field checks, and arithmetic consistency checks on extracted data.
"""

import re
from datetime import datetime
from typing import List, Dict, Any, Tuple

REQUIRED_FIELDS: Dict[str, List[str]] = {
    "invoice": ["invoice_no", "date", "total"],
    "receipt": ["receipt_no", "date", "total"],
    "form": ["name", "date_of_birth"],
    "certificate": ["certificate_id", "awarded_to", "date"],
}

DATE_FORMATS = ["%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%Y-%m-%d", "%Y/%m/%d", "%d/%m/%y"]


def _parse_amount(value) -> float | None:
    if not value:
        return None
    try:
        return float(str(value).replace(",", "").strip())
    except ValueError:
        return None


def _parse_date(value) -> datetime | None:
    if not value:
        return None
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(str(value).strip(), fmt)
        except ValueError:
            continue
    return None


def check_required_fields(doc_type: str, fields: Dict[str, Any]) -> List[str]:
    errors = []
    for required in REQUIRED_FIELDS.get(doc_type, []):
        if not fields.get(required):
            errors.append(f"Missing required field: '{required}'")
    return errors


def check_date_validity(fields: Dict[str, Any]) -> List[str]:
    errors = []
    for field_name in ("date", "date_of_birth"):
        raw = fields.get(field_name)
        if raw:
            parsed = _parse_date(raw)
            if parsed is None:
                errors.append(f"Field '{field_name}' value '{raw}' is not a recognizable date")
            elif parsed > datetime.now():
                errors.append(f"Field '{field_name}' value '{raw}' is in the future")
    return errors


def check_gstin_format(fields: Dict[str, Any]) -> List[str]:
    errors = []
    gstin = fields.get("gstin")
    if gstin and not re.fullmatch(r"\d{2}[A-Z]{5}\d{4}[A-Z]\d[Z][A-Z\d]", gstin):
        errors.append(f"GSTIN '{gstin}' does not match expected format")
    return errors


def check_line_items_sum_to_total(fields: Dict[str, Any], table: List[Dict[str, str]],
                                   amount_column_candidates: List[str] = None,
                                   tolerance: float = 1.0) -> List[str]:
    errors = []
    if not table:
        return errors

    total = _parse_amount(fields.get("total"))
    if total is None:
        return errors

    amount_column_candidates = amount_column_candidates or ["amount", "total", "price"]
    amount_col = next((c for c in amount_column_candidates if c in table[0]), None)
    if amount_col is None:
        
        return errors

    line_sum, parse_failed = 0.0, False
    for row in table:
        val = _parse_amount(row.get(amount_col))
        if val is None:
            parse_failed = True
        else:
            line_sum += val

    if parse_failed:
        errors.append(f"Could not parse all values in table column '{amount_col}'; sum check skipped")
    elif abs(line_sum - total) > tolerance:
        errors.append(
            f"Line items sum to {line_sum:.2f} but extracted total is {total:.2f} "
            f"(difference: {abs(line_sum - total):.2f})"
        )
    return errors


COMMON_RULES = [check_date_validity]

RULES_BY_TYPE = {
    "invoice": [check_gstin_format, check_line_items_sum_to_total],
}


def _run_checks(doc_type: str, fields: Dict[str, Any], table: List[Dict[str, str]]) -> List[str]:
    errors = check_required_fields(doc_type, fields)
    for rule in COMMON_RULES:
        errors += rule(fields)
    for rule in RULES_BY_TYPE.get(doc_type, []):
        # check_line_items_sum_to_total needs the table too; others just need fields
        errors += rule(fields, table) if rule is check_line_items_sum_to_total else rule(fields)
    return errors


def validate(doc_type: str, fields: Dict[str, Dict[str, Any]],
             tables: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], bool]:
   
    plain_fields = {name: f["value"] for name, f in fields.items()}
    plain_table = []
    if tables:
        headers = tables[0]["headers"]
        plain_table = [dict(zip(headers, row)) for row in tables[0]["rows"]]

    error_messages = _run_checks(doc_type, plain_fields, plain_table)

    results = [{"rule": "validation", "passed": False, "message": msg} for msg in error_messages]
    if not results:
        results = [{"rule": "validation", "passed": True, "message": ""}]

    return results, len(error_messages) > 0 

from typing import Callable

from docint.schemas import ExtractedField, ValidationResult

LOW_CONF = 0.6


def _num(f: ExtractedField | None) -> float | None:
    try:
        return float((f.value or "").replace(",", ""))
    except (ValueError, AttributeError):
        return None


def total_matches(fields: dict[str, ExtractedField]) -> ValidationResult:
    sub, tax, tot = _num(fields.get("subtotal")), _num(fields.get("tax")), _num(fields.get("total"))
    if None in (sub, tax, tot):
        return ValidationResult(rule="total_matches", passed=False, message="missing subtotal/tax/total")
    ok = abs(sub + tax - tot) < 0.01
    return ValidationResult(rule="total_matches", passed=ok, message="" if ok else f"{sub}+{tax}!={tot}")


RULES: list[Callable[[dict[str, ExtractedField]], ValidationResult]] = [total_matches]


def validate(fields: dict[str, ExtractedField]) -> tuple[list[ValidationResult], bool]:
    """Return (results, needs_review)."""
    results = [rule(fields) for rule in RULES]
    needs_review = any(not r.passed for r in results) or any(f.conf < LOW_CONF for f in fields.values())
    return results, needs_review
