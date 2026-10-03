"""OWNER: Person D.

API-layer Pydantic models (request bodies and response shapes).
These are separate from the core data contract in docint/schemas.py.
"""
from __future__ import annotations

import re
from datetime import date
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

# Regex for valid field names: must start with lowercase letter, then
# lowercase letters / digits / underscores only.
_FIELD_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")


class PatchFieldsRequest(BaseModel):
    """Body for PATCH /documents/{doc_id}/fields."""

    fields: dict[str, str] = Field(
        ...,
        min_length=1,
        description="Map of field_name -> new string value. At least one entry required.",
    )

    @field_validator("fields")
    @classmethod
    def validate_field_names_and_values(
        cls, v: dict[str, str]
    ) -> dict[str, str]:
        for name, value in v.items():
            if not _FIELD_NAME_RE.match(name):
                raise ValueError(
                    f"Invalid field name {name!r}. "
                    "Names must match ^[a-z][a-z0-9_]*$"
                )
            if len(value) > 500:
                raise ValueError(
                    f"Value for field {name!r} exceeds 500 characters."
                )
        return v


class SearchItem(BaseModel):
    """One row in the search results list."""

    doc_id: str
    filename: str
    doc_type: str
    needs_review: bool
    vendor: Optional[str] = None
    doc_date: Optional[str] = None
    total_amount: Optional[float] = None
    created_at: str  # ISO datetime string


class SearchResponse(BaseModel):
    """Paginated search response."""

    total: int
    limit: int
    offset: int
    items: list[SearchItem]


class SearchQuery(BaseModel):
    """Parsed and validated search query parameters."""

    q: Optional[str] = None
    doc_type: Optional[str] = None
    needs_review: Optional[bool] = None
    vendor: Optional[str] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def check_ranges(self) -> "SearchQuery":
        if (
            self.date_from is not None
            and self.date_to is not None
            and self.date_from > self.date_to
        ):
            raise ValueError("date_from must not be after date_to")
        if (
            self.min_amount is not None
            and self.max_amount is not None
            and self.min_amount > self.max_amount
        ):
            raise ValueError("min_amount must not be greater than max_amount")
        return self
