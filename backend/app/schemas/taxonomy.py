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


class TermCreate(BaseModel):
    key: str
    label: str  # the display label text (NOT the Capability/Source node label)
    description: str | None = None
    parent_key: str | None = None


class MergeRequest(BaseModel):
    into_key: str
