"""
Extraction Pipeline Orchestrator

Serves as the primary public entry point for Part C field and table extraction.
"""


from typing import List, Dict, Any, Tuple
from ._tokens import tokens_to_words
from .fields import extract_fields
from .tables import extract_table


def _fields_to_contract_shape(fields: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    
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
