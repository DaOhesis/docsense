"""OWNER: Person D.  Run:  uvicorn docint.api.main:app --reload --app-dir src
"""
from __future__ import annotations

import os
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from docint.api.models import (
    PatchFieldsRequest,
    SearchItem,
    SearchResponse,
    SearchQuery,
)
from docint.db.models import DocumentRecord
from docint.db.service import save_result
from docint.db.session import get_db, init_db
from docint.pipeline import process_document
from docint.schemas import DocumentResult, ExtractedField
from docint.validation.rules import validate

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "./uploads"))

ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".pdf"}
ALLOWED_CONTENT_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
    ".bmp": "image/bmp",
    ".pdf": "application/pdf",
}
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB


# ---------------------------------------------------------------------------
# App lifecycle
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(
    title="Smart Document & Form Intelligence System",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------
@app.get("/health")
def health():
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Stage 1: Upload with file storage
# ---------------------------------------------------------------------------
@app.post("/documents", response_model=DocumentResult)
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    # --- validate extension ---
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail=(
                f"Unsupported file type {suffix!r}. "
                f"Allowed: {sorted(ALLOWED_EXTENSIONS)}"
            ),
        )

    data = await file.read()

    # --- validate size ---
    if len(data) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({len(data)} bytes). Maximum is {MAX_FILE_SIZE} bytes.",
        )

    # --- run the pipeline ---
    result = process_document(data, file.filename or "upload")

    # --- persist file (never use the client filename in the path) ---
    stored_path = UPLOAD_DIR / f"{result.doc_id}{suffix}"
    stored_path.write_bytes(data)

    content_type = ALLOWED_CONTENT_TYPES.get(suffix, "application/octet-stream")

    # --- persist to DB ---
    save_result(
        db,
        result,
        file_path=str(stored_path),
        content_type=content_type,
    )
    return result


# ---------------------------------------------------------------------------
# Stage 1: Get stored document file
# ---------------------------------------------------------------------------
@app.get("/documents/{doc_id}/file")
def get_document_file(doc_id: str, db: Session = Depends(get_db)):
    rec = db.get(DocumentRecord, doc_id)
    if not rec or not rec.file_path:
        raise HTTPException(status_code=404, detail="File not found")

    file_path = Path(rec.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")

    return FileResponse(
        path=str(file_path),
        media_type=rec.content_type or "application/octet-stream",
        filename=rec.filename,
    )


# ---------------------------------------------------------------------------
# Stage 1: Get document result by ID
# ---------------------------------------------------------------------------
@app.get("/documents/{doc_id}", response_model=DocumentResult)
def get_document(doc_id: str, db: Session = Depends(get_db)):
    rec = db.get(DocumentRecord, doc_id)
    if not rec:
        raise HTTPException(404, "Document not found")
    return DocumentResult.model_validate_json(rec.result_json)


# ---------------------------------------------------------------------------
# Stage 2: PATCH /documents/{doc_id}/fields
# ---------------------------------------------------------------------------
@app.patch("/documents/{doc_id}/fields", response_model=DocumentResult)
def patch_document_fields(
    doc_id: str,
    body: PatchFieldsRequest,
    db: Session = Depends(get_db),
):
    rec = db.get(DocumentRecord, doc_id)
    if not rec:
        raise HTTPException(404, "Document not found")

    # Reconstruct the full result from canonical JSON
    result = DocumentResult.model_validate_json(rec.result_json)

    # Apply field corrections (set conf=1.0 for human-verified values)
    for field_name, new_value in body.fields.items():
        existing = result.fields.get(field_name)
        existing_bbox = existing.bbox if existing else None
        result.fields[field_name] = ExtractedField(
            value=new_value,
            conf=1.0,
            bbox=existing_bbox,
        )

    # Re-run validation with updated fields
    validation_results, needs_review = validate(result.fields)
    result = result.model_copy(
        update={
            "validation": validation_results,
            "needs_review": needs_review,
        }
    )

    # Persist (single transaction via save_result)
    save_result(db, result, file_path=rec.file_path, content_type=rec.content_type)
    return result


# ---------------------------------------------------------------------------
# Stage 2: GET /search with advanced filters + pagination
# ---------------------------------------------------------------------------
@app.get("/search", response_model=SearchResponse)
def search(
    q: Optional[str] = Query(default=None),
    doc_type: Optional[str] = Query(default=None),
    needs_review: Optional[bool] = Query(default=None),
    vendor: Optional[str] = Query(default=None),
    date_from: Optional[str] = Query(default=None),
    date_to: Optional[str] = Query(default=None),
    min_amount: Optional[float] = Query(default=None),
    max_amount: Optional[float] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    # Validate via pydantic model so we get 422 on bad ranges
    try:
        from datetime import date as _date
        params = SearchQuery(
            q=q,
            doc_type=doc_type,
            needs_review=needs_review,
            vendor=vendor,
            date_from=_date.fromisoformat(date_from) if date_from else None,
            date_to=_date.fromisoformat(date_to) if date_to else None,
            min_amount=min_amount,
            max_amount=max_amount,
            limit=limit,
            offset=offset,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    stmt = select(DocumentRecord)

    if params.doc_type:
        stmt = stmt.where(DocumentRecord.doc_type == params.doc_type)
    if params.needs_review is not None:
        stmt = stmt.where(DocumentRecord.needs_review == params.needs_review)
    if params.vendor:
        stmt = stmt.where(
            DocumentRecord.vendor.ilike(f"%{params.vendor}%")
        )
    if params.date_from:
        stmt = stmt.where(DocumentRecord.doc_date >= params.date_from.isoformat())
    if params.date_to:
        stmt = stmt.where(DocumentRecord.doc_date <= params.date_to.isoformat())
    if params.min_amount is not None:
        stmt = stmt.where(DocumentRecord.total_amount >= params.min_amount)
    if params.max_amount is not None:
        stmt = stmt.where(DocumentRecord.total_amount <= params.max_amount)
    if params.q:
        stmt = stmt.where(DocumentRecord.result_json.ilike(f"%{params.q}%"))

    # Total count (before pagination)
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total: int = db.scalar(count_stmt) or 0

    # Fetch page
    rows = db.scalars(
        stmt.order_by(
            DocumentRecord.created_at.desc(),
            DocumentRecord.id.desc(),
        )
        .limit(params.limit)
        .offset(params.offset)
    ).all()

    items = [
        SearchItem(
            doc_id=r.id,
            filename=r.filename,
            doc_type=r.doc_type,
            needs_review=r.needs_review,
            vendor=r.vendor,
            doc_date=r.doc_date,
            total_amount=float(r.total_amount) if r.total_amount is not None else None,
            created_at=r.created_at.isoformat(),
        )
        for r in rows
    ]

    return SearchResponse(total=total, limit=params.limit, offset=params.offset, items=items)
