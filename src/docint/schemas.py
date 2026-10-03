"""
THE DATA CONTRACT.
Every module in the pipeline reads/writes these models.
Do NOT change this file without telling the whole team (see docs/schema.md).
"""
from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class DocType(str, Enum):
    invoice = "invoice"
    receipt = "receipt"
    form = "form"
    certificate = "certificate"
    unknown = "unknown"


class OCRToken(BaseModel):
    text: str
    bbox: list[float] = Field(..., min_length=4, max_length=4, description="[x1, y1, x2, y2] in pixels")
    conf: float = Field(..., ge=0, le=1)


class ExtractedField(BaseModel):
    value: Optional[str] = None
    conf: float = Field(0.0, ge=0, le=1)
    bbox: Optional[list[float]] = None


class Table(BaseModel):
    headers: list[str]
    rows: list[list[str]]


class ValidationResult(BaseModel):
    rule: str
    passed: bool
    message: str = ""


class DocumentResult(BaseModel):
    doc_id: str
    filename: str = ""
    doc_type: DocType = DocType.unknown
    doc_type_conf: float = 0.0
    ocr: list[OCRToken] = []
    fields: dict[str, ExtractedField] = {}
    tables: list[Table] = []
    validation: list[ValidationResult] = []
    needs_review: bool = False
