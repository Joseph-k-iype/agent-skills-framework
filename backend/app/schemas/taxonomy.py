from __future__ import annotations

from pydantic import BaseModel


class TermOut(BaseModel):
    key: str
    label: str
    description: str | None
    status: str
    parent_key: str | None


class TaxonomyTreeOut(BaseModel):
    terms: list[TermOut]
