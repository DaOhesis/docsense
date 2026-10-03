"""OWNER: Person D.

Tables
------
- DocumentRecord       : one row per processed document (canonical store)
- DocumentFieldRecord  : normalised extracted fields  (1-N → document)
- LineItemRecord       : normalised table line items  (1-N → document)

TODO: add separate tables for validation results if needed in future.
NOTE: After pulling this change, delete your local docint.db and restart
      the API so SQLAlchemy recreates all tables.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from docint.db.session import Base


class DocumentRecord(Base):
    """One row per processed document.

    result_json is the canonical full DocumentResult payload.
    vendor, doc_date, total_amount are denormalised summary columns for fast
    search/filtering without parsing JSON at query time.
    """

    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    filename: Mapped[str] = mapped_column(String, default="")
    doc_type: Mapped[str] = mapped_column(String, index=True, default="unknown")
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False)
    result_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    # --- new columns (Stage 1) ---
    file_path: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    content_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    vendor: Mapped[Optional[str]] = mapped_column(String, index=True, nullable=True)
    doc_date: Mapped[Optional[str]] = mapped_column(String, index=True, nullable=True)
    # Numeric(12, 2, asdecimal=False) avoids Decimal objects on SQLite and
    # gives proper NUMERIC on PostgreSQL – no dialect-specific SQL.
    total_amount: Mapped[Optional[float]] = mapped_column(
        Numeric(12, 2, asdecimal=False), index=True, nullable=True
    )

    # --- relationships ---
    fields: Mapped[list[DocumentFieldRecord]] = relationship(
        "DocumentFieldRecord",
        back_populates="document",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    line_items: Mapped[list[LineItemRecord]] = relationship(
        "LineItemRecord",
        back_populates="document",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class DocumentFieldRecord(Base):
    """Normalised extracted field – one row per (document, field_name).

    Unique constraint on (document_id, name) so upsert is safe.
    """

    __tablename__ = "document_fields"
    __table_args__ = (UniqueConstraint("document_id", "name", name="uq_doc_field"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[str] = mapped_column(
        String, ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String)
    value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)

    document: Mapped[DocumentRecord] = relationship(
        "DocumentRecord", back_populates="fields"
    )


class LineItemRecord(Base):
    """Normalised table line item.

    data is stored as a JSON string (header → cell mapping) to stay portable
    across SQLite (no native JSON type) and PostgreSQL.
    """

    __tablename__ = "line_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[str] = mapped_column(
        String, ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    table_index: Mapped[int] = mapped_column(Integer, default=0)
    row_index: Mapped[int] = mapped_column(Integer, default=0)
    # JSON string: {"item": "Widget", "qty": "10", "price": "100.00"}
    data: Mapped[str] = mapped_column(Text, default="{}")

    document: Mapped[DocumentRecord] = relationship(
        "DocumentRecord", back_populates="line_items"
    )
