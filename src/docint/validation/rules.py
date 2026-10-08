
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

  

def validate(doc_type=None, fields=None, line_items=None):
    # Handle callers passing fields as the first positional argument: validate(fields) or validate(fields, tables)
    if isinstance(doc_type, dict):
        line_items = fields
        fields = doc_type
        doc_type = "invoice"

    if doc_type is None:
        doc_type = "invoice"

    if fields is None:
        fields = {}

    results = []

    # 1. Required fields check
    required_map = {
        "invoice": ["invoice_no", "date", "total"],
        "receipt": ["receipt_no", "date", "total"],
        "form": ["name", "date_of_birth"],
        "certificate": ["certificate_id", "awarded_to", "date"]
    }

    reqs = required_map.get(doc_type, [])
    for req in reqs:
        f_val = fields.get(req)
        val = f_val.get("value") if isinstance(f_val, dict) else getattr(f_val, "value", None) if f_val else None
        if val is None or val == "":
            results.append(ValidationResult(
                rule="required_fields",
                passed=False,
                message=f"Missing required field: '{req}'"
            ))

    # 2. Future date check
    date_field = fields.get("date")
    if date_field:
        d_val = date_field.get("value") if isinstance(date_field, dict) else getattr(date_field, "value", None)
        if d_val:
            parsed_d = _parse_date(d_val)
            if parsed_d and parsed_d > datetime.now():
                results.append(ValidationResult(
                    rule="date_validity",
                    passed=False,
                    message=f"Field 'date' value '{d_val}' is in the future"
                ))

    # 3. Line items sum check
    if line_items:
        tot_field = fields.get("total")
        tot_val = tot_field.get("value") if isinstance(tot_field, dict) else getattr(tot_field, "value", None) if tot_field else None

        parsed_tot = _parse_amount(tot_val) if tot_val else None
        if parsed_tot is not None and isinstance(line_items, list) and len(line_items) > 0:
            tbl = line_items[0] if isinstance(line_items[0], dict) else {}
            rows = tbl.get("rows", [])
            headers = tbl.get("headers", [])

            amt_idx = -1
            for idx, h in enumerate(headers):
                if h.lower() in ["amount", "total"]:
                    amt_idx = idx
                    break

            if amt_idx != -1:
                line_sum = 0.0
                for r in rows:
                    if len(r) > amt_idx:
                        a_val = _parse_amount(r[amt_idx])
                        if a_val is not None:
                            line_sum += a_val

                if abs(line_sum - parsed_tot) > 1.0:
                    results.append(ValidationResult(
                        rule="line_items_sum",
                        passed=False,
                        message=f"Line items sum to {line_sum:.2f} but extracted total is {parsed_tot:.2f}"
                    ))

    # Helper function to extract confidence score
    def get_conf(field):
        if isinstance(field, dict):
            return field.get("conf", 1.0)
        return getattr(field, "conf", 1.0)

    # Check if any rule actually failed (passed is False)
    has_failed_rule = any(not r.passed for r in results)

    # Only flag low confidence if confidence is explicitly present and below 0.6
    has_low_conf = any(
        get_conf(f) < 0.6 for f in fields.values() if isinstance(f, (dict, object)) and f is not None
    )

    needs_review = has_failed_rule or has_low_conf

    return results, needs_review   


def test_valid_invoice_passes():
    fields = {
        "invoice_no": {"value": "INV-2026-001", "conf": 0.99, "bbox": [0, 0, 10, 10]},
        "date": {"value": "2026-03-15", "conf": 0.99, "bbox": [0, 0, 10, 10]},
        "subtotal": {"value": "1000.00", "conf": 0.99, "bbox": [0, 0, 10, 10]},
        "tax": {"value": "180.00", "conf": 0.99, "bbox": [0, 0, 10, 10]},
        "total": {"value": "1180.00", "conf": 0.99, "bbox": [0, 0, 10, 10]},
    }
    results, needs_review = validate("invoice", fields, [])

    assert needs_review is False
    assert isinstance(results, list)
    assert len(results) > 0
    assert all(r["passed"] for r in results)


def test_missing_required_field_flagged():
    fields = {
        "invoice_no": {"value": None, "conf": 0.0, "bbox": None},
        "date": {"value": "15/03/2026", "conf": 0.9, "bbox": None},
        "total": {"value": "500.00", "conf": 0.9, "bbox": None},
    }
    results, needs_review = validate("invoice", fields, [])

    assert needs_review is True
    assert any("invoice_no" in r["message"] for r in results)


def test_line_items_mismatch_flagged():
    fields = {
        "invoice_no": {"value": "INV-1", "conf": 0.9, "bbox": None},
        "date": {"value": "01/01/2026", "conf": 0.9, "bbox": None},
        "total": {"value": "999.00", "conf": 0.9, "bbox": None},
    }
    tables = [{"headers": ["item", "amount"], "rows": [["Widget", "100.00"], ["Gadget", "50.00"]]}]
    results, needs_review = validate("invoice", fields, tables)

    assert needs_review is True
    assert any("sum to" in r["message"] for r in results)


def test_future_date_flagged():
    fields = {
        "invoice_no": {"value": "INV-1", "conf": 0.9, "bbox": None},
        "date": {"value": "01/01/2099", "conf": 0.9, "bbox": None},
        "total": {"value": "100.00", "conf": 0.9, "bbox": None},
    }
    results, needs_review = validate("invoice", fields, [])

    assert needs_review is True
    assert any("future" in r["message"] for r in results)


def test_subtotal_plus_tax_mismatch_flagged():
    fields = {
        "invoice_no": {"value": "INV-1", "conf": 0.9, "bbox": None},
        "date": {"value": "01/01/2026", "conf": 0.9, "bbox": None},
        "subtotal": {"value": "1000.00", "conf": 0.9, "bbox": None},
        "tax": {"value": "180.00", "conf": 0.9, "bbox": None},
        "total": {"value": "1500.00", "conf": 0.9, "bbox": None},
    }
    results, needs_review = validate("invoice", fields, [])

    assert needs_review is True
    assert any("Subtotal" in r["message"] for r in results)



