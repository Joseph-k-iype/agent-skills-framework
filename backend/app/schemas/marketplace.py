from __future__ import annotations

from pydantic import BaseModel, Field


class ApiKeyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class UsageBody(BaseModel):
    listing_id: str
    kind: str = "apply"
    meta: dict = Field(default_factory=dict)
