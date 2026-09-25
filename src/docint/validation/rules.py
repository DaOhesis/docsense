"""OWNER: Person C  |  Branch prefix: feature/validation-*

Each rule is a function: fields -> ValidationResult. Add new rules to RULES.
TODO ideas: date format, required fields per doc type, GSTIN/ID format,
            line items sum == subtotal, duplicate invoice numbers.
"""
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
