"""
tables.py
---------
Reconstructs tables (e.g. invoice line items) from OCR word bounding boxes.

Approach:
1. Group words into visual lines (rows) by similar y-position.
2. Find the header row by matching common table-header keywords.
3. Use the header words' x-positions as column boundaries.
4. Assign words in subsequent rows to the nearest header column by
   x-center, then join words in the same column into one cell string.
"""

from typing import List, Dict, Optional
from ._tokens import OCRWord
from .fields import _line_up_words

TABLE_HEADER_KEYWORDS = [
    "item", "description", "qty", "quantity", "rate", "price",
    "unit price", "amount", "total", "sr", "sl", "no", "hsn",
]


def _find_header_line(lines: List[List[OCRWord]]) -> Optional[int]:
    best_idx, best_score = None, 0
    for idx, line in enumerate(lines):
        line_text = " ".join(w.text.lower() for w in line)
        score = sum(1 for kw in TABLE_HEADER_KEYWORDS if kw in line_text)
        if score >= 2 and score > best_score:
            best_idx, best_score = idx, score
    return best_idx


def _assign_to_column(word: OCRWord, column_bounds: List[float]) -> int:
    col = 0
    for i, bound in enumerate(column_bounds):
        if word.x_center >= bound:
            col = i
    return col


def extract_table(words: List[OCRWord]) -> List[Dict[str, str]]:
    """
    Find and reconstruct a single table from a page of OCR words.
    Returns an empty list if no header row could be confidently detected.
    """
    lines = _line_up_words(words)
    header_idx = _find_header_line(lines)
    if header_idx is None:
        return []

    header_line = lines[header_idx]
    column_names = [w.text.strip(":").lower() for w in header_line]
    column_bounds = [w.x0 for w in header_line]

    rows: List[Dict[str, str]] = []
    for line in lines[header_idx + 1:]:
        line_text = " ".join(w.text.lower() for w in line)
        if any(stop_word in line_text for stop_word in
               ["grand total", "subtotal", "total due", "total:", "total "]):
            break

        row_cells: Dict[str, List[str]] = {name: [] for name in column_names}
        for w in line:
            col_idx = min(_assign_to_column(w, column_bounds), len(column_names) - 1)
            row_cells[column_names[col_idx]].append(w.text)

        row = {name: " ".join(vals).strip() for name, vals in row_cells.items()}
        if any(v for v in row.values()):
            rows.append(row)

    return rows
