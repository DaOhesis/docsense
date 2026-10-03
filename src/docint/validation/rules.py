"""
rules.py
--------
Validation: required-field checks per document type, plus cross-field
business rules (e.g. does the invoice total equal the sum of line items).

Add new checks to RULES_BY_TYPE or the standalone check_* functions below --
per TEAM_GUIDE.md, this is the file the guide means by "add to RULES in
validation/rules.py".
"""

import re
from datetime import datetime
from typing import List, Dict, Any, Tuple

# Required fields per document type. Keys must match the field names
# extraction/fields.py actually produces (see REGEX_PATTERNS / LABEL_FIELD_MAP).
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


# Rules that apply regardless of document type
COMMON_RULES = [check_date_validity]

# Rules specific to one document type
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
    """
    THE CONTRACT FUNCTION. TEAM_GUIDE.md lists validate(fields) with one
    argument, but the actual rules (line items = total, required fields per
    type) need doc_type and the table too -- raise this gap with your team;
    this signature is the practical fix until everyone agrees on schemas.py.

    fields: contract-shaped {name: {"value":..., "conf":..., "bbox":...}}
    tables: contract-shaped [{"headers": [...], "rows": [[...]]}]

    Returns (list[ValidationResult], needs_review) per the contract.
    """
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
