"""OWNER: Person D.

Database service layer – business logic that sits between the API and the ORM.

Public API
----------
save_result(db, result, file_path=None, content_type=None) -> DocumentRecord
parse_amount(value: str | None) -> float | None
parse_date(value: str | None) -> str | None   # always ISO yyyy-mm-dd or None
"""
from __future__ import annotations

import json
import re
from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from docint.db.models import DocumentFieldRecord, DocumentRecord, LineItemRecord
from docint.schemas import DocumentResult


# ---------------------------------------------------------------------------
# Helpers – must never raise, always return None on bad input
# ---------------------------------------------------------------------------

def parse_amount(value: Optional[str]) -> Optional[float]:
    """Strip currency symbols / commas / whitespace and convert to float.

    Returns None on empty input or any parse failure.

    Examples
    --------
    >>> parse_amount("1,180.00")
    1180.0
    >>> parse_amount("$ 1 180.00")  # space-thousand-sep
    1180.0
    >>> parse_amount(None)

    >>> parse_amount("N/A")

    """
    if not value:
        return None
    try:
        # Remove everything except digits, dot, minus
        cleaned = re.sub(r"[^\d.\-]", "", value.strip())
        if not cleaned or cleaned in (".", "-"):
            return None
        return float(cleaned)
    except (ValueError, TypeError):
        return None


def parse_date(value: Optional[str]) -> Optional[str]:
    """Try several date formats and return ISO yyyy-mm-dd string or None.

    Formats tried (in order):
        yyyy-mm-dd        (ISO)
        dd/mm/yyyy
        dd-mm-yyyy
        dd Mon yyyy       (e.g. "15 Sep 2025")
        dd Month yyyy     (e.g. "15 September 2025")

    Returns None on empty input or any parse failure.
    """
    if not value:
        return None
    value = value.strip()
    formats = [
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%d %b %Y",
        "%d %B %Y",
    ]
    from datetime import datetime as _dt
    for fmt in formats:
        try:
            return _dt.strptime(value, fmt).date().isoformat()
        except (ValueError, TypeError):
            continue
    return None


# ---------------------------------------------------------------------------
# Main persistence function
# ---------------------------------------------------------------------------

def save_result(
    db: Session,
    result: DocumentResult,
    *,
    file_path: Optional[str] = None,
    content_type: Optional[str] = None,
) -> DocumentRecord:
    """Upsert a DocumentResult (and all child records) in ONE transaction.

    Summary column mapping
    ----------------------
    vendor       <- fields["vendor"] or fields["merchant"]
    doc_date     <- fields["date"]  (parsed to ISO string)
    total_amount <- fields["total"] (parsed to float)

    The canonical full result is always stored in result_json so that
    DocumentResult.model_validate_json() can reconstruct the full object.
    """
    # --- resolve summary columns from extracted fields ---
    vendor_field = result.fields.get("vendor") or result.fields.get("merchant")
    vendor_val = vendor_field.value if vendor_field else None

    date_field = result.fields.get("date")
    date_val = parse_date(date_field.value if date_field else None)

    total_field = result.fields.get("total")
    total_val = parse_amount(total_field.value if total_field else None)

    # --- upsert DocumentRecord ---
    rec = db.get(DocumentRecord, result.doc_id)
    if rec is None:
        rec = DocumentRecord(id=result.doc_id)
        db.add(rec)

    rec.filename = result.filename
    rec.doc_type = result.doc_type.value
    rec.needs_review = result.needs_review
    rec.result_json = result.model_dump_json()
    rec.vendor = vendor_val
    rec.doc_date = date_val
    rec.total_amount = total_val

    if file_path is not None:
        rec.file_path = file_path
    if content_type is not None:
        rec.content_type = content_type

    # --- flush so FK constraints are satisfied before children ---
    db.flush()

    # --- rebuild child field rows (delete-then-insert is simplest and safe
    #     because we have the full result object) ---
    db.query(DocumentFieldRecord).filter(
        DocumentFieldRecord.document_id == result.doc_id
    ).delete(synchronize_session=False)

    for name, ef in result.fields.items():
        db.add(
            DocumentFieldRecord(
                document_id=result.doc_id,
                name=name,
                value=ef.value,
                confidence=ef.conf,
            )
        )

    # --- rebuild line item rows ---
    db.query(LineItemRecord).filter(
        LineItemRecord.document_id == result.doc_id
    ).delete(synchronize_session=False)

    for t_idx, table in enumerate(result.tables):
        for r_idx, row in enumerate(table.rows):
            cell_map = dict(zip(table.headers, row))
            db.add(
                LineItemRecord(
                    document_id=result.doc_id,
                    table_index=t_idx,
                    row_index=r_idx,
                    data=json.dumps(cell_map),
                )
            )

    db.commit()
    db.refresh(rec)
    return rec
