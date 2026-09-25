"""OWNER: Person D.  Run:  uvicorn docint.api.main:app --reload --app-dir src"""
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from docint.db.models import DocumentRecord
from docint.db.session import get_db, init_db
from docint.pipeline import process_document
from docint.schemas import DocumentResult


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Smart Document & Form Intelligence System", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/documents", response_model=DocumentResult)
async def upload_document(file: UploadFile = File(...), db: Session = Depends(get_db)):
    data = await file.read()
    result = process_document(data, file.filename or "upload")
    db.add(
        DocumentRecord(
            id=result.doc_id,
            filename=result.filename,
            doc_type=result.doc_type.value,
            needs_review=result.needs_review,
            result_json=result.model_dump_json(),
        )
    )
    db.commit()
    return result


@app.get("/documents/{doc_id}", response_model=DocumentResult)
def get_document(doc_id: str, db: Session = Depends(get_db)):
    rec = db.get(DocumentRecord, doc_id)
    if not rec:
        raise HTTPException(404, "Document not found")
    return DocumentResult.model_validate_json(rec.result_json)


@app.get("/search")
def search(
    q: Optional[str] = None,
    doc_type: Optional[str] = None,
    needs_review: Optional[bool] = None,
    db: Session = Depends(get_db),
):
    """Simple search. TODO (Person D): field-level filters, date/amount ranges, pagination."""
    stmt = select(DocumentRecord)
    if doc_type:
        stmt = stmt.where(DocumentRecord.doc_type == doc_type)
    if needs_review is not None:
        stmt = stmt.where(DocumentRecord.needs_review == needs_review)
    if q:
        stmt = stmt.where(DocumentRecord.result_json.ilike(f"%{q}%"))
    rows = db.scalars(stmt.order_by(DocumentRecord.created_at.desc()).limit(50)).all()
    return [{"doc_id": r.id, "filename": r.filename, "doc_type": r.doc_type, "needs_review": r.needs_review} for r in rows]
