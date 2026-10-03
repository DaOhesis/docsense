"""
extract.py
----------
THE public interface for this package. Everyone else (the lead's
pipeline.py, D's API layer, tests) should only ever import extract() from
here -- fields.py, tables.py and _tokens.py are implementation details.

Matches TEAM_GUIDE.md section 2 exactly:
    extract(doc_type, tokens) -> (dict[str, ExtractedField], list[Table])

doc_type: decided upstream by B's classify() -- this function does NOT
          classify documents, only extracts fields/tables from one.
tokens:   list[OCRToken] in contract format, e.g.
          {"text": "INV-1024", "bbox": [10, 50, 120, 80], "conf": 0.95}
"""

from typing import List, Dict, Any, Tuple
from ._tokens import tokens_to_words
from .fields import extract_fields
from .tables import extract_table


def _fields_to_contract_shape(fields: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """
    {name: value} -> {name: {"value":..., "conf":..., "bbox": None}}

    NOTE: per-field confidence/bbox aren't tracked yet -- conf here is a
    placeholder (0.9 if found, 0.0 if not). A good later improvement: carry
    through the OCR confidence of whichever word(s) produced the value.
    """
    return {
        name: {"value": value, "conf": 0.9 if value else 0.0, "bbox": None}
        for name, value in fields.items()
    }


def _table_to_contract_shape(table_rows: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    """[{col: val}, ...] -> [{"headers": [...], "rows": [[...], ...]}] (or [] if no table)."""
    if not table_rows:
        return []
    headers = list(table_rows[0].keys())
    rows = [[row.get(h, "") for h in headers] for row in table_rows]
    return [{"headers": headers, "rows": rows}]


def extract(doc_type: str, tokens: List[Dict[str, Any]]) -> Tuple[Dict[str, Dict[str, Any]], List[Dict[str, Any]]]:
    """Extract fields and tables from OCR tokens for a document of the given type."""
    words = tokens_to_words(tokens)
    full_text = " ".join(w.text for w in words)

    raw_fields = extract_fields(full_text, words)
    raw_table = extract_table(words)

    return _fields_to_contract_shape(raw_fields), _table_to_contract_shape(raw_table)
